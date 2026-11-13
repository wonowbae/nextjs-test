ㅇㅇ. anaconda 기본포함된 패키지 전체

34s 동안 처리함
그러면 Anaconda를 처음 설치했을 때의 패키지 전체를 새 환경에 재현하는 게 목표네. base에 나중에 추가한 패키지들은 제외하고.

폐쇄망에서는 다음 순서로 해보면 돼.

1. Anaconda 메타패키지 확인
conda list -n base anaconda
conda search --offline anaconda

anaconda 메타패키지는 Anaconda 배포판에 포함된 패키지 구성을 지정하는 패키지야. 다만 2023년 2월 이후 Anaconda 설치 프로그램에서는 기본 제공되지 않아. 

Anaconda documentation

2. 메타패키지가 로컬에 있다면
conda create -n clean --offline anaconda

이렇게 하면 메타패키지가 지정한 기본 패키지들과 의존성을 설치해.

단, 메타패키지와 필요한 패키지들이 모두 로컬 캐시에 있어야 하고, 메타패키지 버전이 현재 설치된 Anaconda 배포판과 같아야 정확한 구성을 재현할 수 있어.

3. 메타패키지가 없다면
네가 가지고 있는 Anaconda 설치 파일을 이용해 별도 경로에 새로 설치하는 방법이 가장 확실해.

예를 들어 기존 설치가 C:\Users\...\anaconda3라면 다른 디렉터리에 초기 Anaconda를 설치한 뒤, 새 설치의 base를 기존 Conda에서 복제하는 방식이야.

conda create -n clean --clone C:\AnacondaClean

C:\AnacondaClean은 새 Anaconda 설치 경로의 예시야. 설치 당시의 기본 패키지 전체가 복제돼.

우선 다음 명령어의 결과를 알려줘.

conda list --revisions

여기서 base의 최초 설치 이력이 남아 있는지 확인해 보자. 남아 있다면 별도의 Anaconda 재설치 없이 최초 패키지 구성을 재현하는 방법도 검토할 수 있어.
