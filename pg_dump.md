1. Jenkinsfile 작성
Windows 환경이고, 매일 새벽 3시대에 백업하며, 30일간 보관한다고 가정할게.
```
pipeline {
    agent any

    triggers {
        cron('H 3 * * *')
    }

    options {
        disableConcurrentBuilds()
    }

    environment {
        PGHOST = 'localhost'
        PGPORT = '5432'
        PGDATABASE = 'mydb'
        BACKUP_DIR = 'D:/backup/postgres'
    }

    stages {
        stage('Backup') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'postgres-backup',
                    usernameVariable: 'PGUSER',
                    passwordVariable: 'PGPASSWORD'
                )]) {
                    powershell '''
                        $ErrorActionPreference = "Stop"

                        New-Item -ItemType Directory -Force $env:BACKUP_DIR | Out-Null

                        $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
                        $file = Join-Path $env:BACKUP_DIR "mydb_$timestamp.dump"

                        pg_dump -Fc -w -f "$file.tmp"

                        if ($LASTEXITCODE -ne 0) {
                            Remove-Item "$file.tmp" -ErrorAction SilentlyContinue
                            throw "Database backup failed"
                        }

                        Move-Item "$file.tmp" $file
                    '''
                }
            }
        }

        stage('Cleanup') {
            steps {
                powershell '''
                    Get-ChildItem $env:BACKUP_DIR -Filter "mydb_*.dump" |
                        Where-Object {
                            $_.LastWriteTime -lt (Get-Date).AddDays(-30)
                        } |
                        Remove-Item
                '''
            }
        }
    }
}
```

백업 중에는 .tmp 파일로 저장하고, 성공했을 때만 .dump로 변경하도록 했어. 실패한 백업을 정상적인 백업으로 착각하지 않도록 하기 위해서야.

pg_dump가 Jenkins 서비스의 PATH에 등록되어 있다는 가정이야. 등록되어 있지 않다면 실행 파일의 절대 경로를 사용하면 돼.
2. Jenkins 설정
Jenkins에서 다음과 같이 설정하면 돼.
- New Item → Pipeline 선택
- Job 이름을 postgres-backup으로 지정
- Credentials에 DB 계정을 Username with password 유형으로 등록
- Credential ID를 postgres-backup으로 설정
- Pipeline에 Jenkinsfile 등록
- 최초 Build Now로 정상 실행 확인
Jenkins의 Credentials Binding을 사용하면 DB 비밀번호를 Jenkinsfile에 직접 작성할 필요가 없어. 
Jenkins+1

3. 실행 주기 설정
```
Cron	실행 주기
H 3 * * *	매일 새벽 3시대
0 3 * * *	매일 새벽 3시 정각
H */6 * * *	6시간마다
H * * * *	1시간마다
H/30 * * * *	30분마다
H 3 * * 0	매주 일요일 새벽 3시대
```
Jenkins에서는 여러 Job이 동시에 실행되는 것을 분산하기 위해 H를 사용할 수 있어. 
Jenkins

4. 백업 파일 관리
실행하면 다음과 같은 구조로 파일이 쌓이게 돼.
```
D:/backup/postgres/


mydb_20261124_031500.dump


mydb_20261125_031500.dump


mydb_20261126_031500.dump
```

30일이 지난 백업은 새로운 백업이 성공한 뒤 자동 삭제
-Fc는 PostgreSQL의 Custom Format이야. 압축을 지원하고, pg_restore를 사용해서 복원할 수 있어. DB를 운영하는 중에도 일관된 스냅샷을 백업할 수 있으므로 서버를 종료할 필요도 없어. 
PostgreSQL+1

5. 복원 방법
별도의 복원 테스트용 DB를 만들어서 백업이 정상적인지 확인하는 것도 중요해.
```
createdb mydb_restore_test

pg_restore --exit-on-error -d mydb_restore_test mydb_20261126_031500.dump
```

pg_dump는 단일 데이터베이스를 백업하므로 DB 사용자, Role 등의 전역 설정까지 백업하려면 별도로 pg_dumpall --globals-only가 필요해.
6. 추천하는 서버 관리 구조
기존 배포 스크립트와 마찬가지로 백업 Jenkinsfile도 Gitea에서 관리하는 게 좋아.
```
infrastructure/
├── jenkins/
│   ├── frontend.Jenkinsfile
│   ├── backend.Jenkinsfile
│   └── postgres-backup.Jenkinsfile
├── scripts/
│   ├── deploy-next.ps1
│   └── deploy-fastapi.ps1
└── nginx/
    └── nginx.conf
```

Jenkins Job도 각각 독립적으로 운영하면 되고.

한 가지 중요한 점은 백업 파일을 DB와 동일한 물리적 디스크에만 보관하지 않는 것이야. 디스크 자체가 고장 나면 원본과 백업을 모두 잃을 수 있으니까.

폐쇄망 내부의 소규모 서비스이고 하루 정도의 데이터 손실을 감수할 수 있다면, 일단 Jenkins + pg_dump + 별도 저장장치 + 주기적인 복원 테스트 정도로 시작해도 충분히 합리적이야.
