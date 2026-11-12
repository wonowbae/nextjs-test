
# 1단계: Windows 11에서 Gitea 패키지 기능 켜기

Gitea가 설치된 폴더 안의 custom/conf/app.ini 파일을 메모장이나 에디터로 열어 아래 설정을 추가(또는 수정)합니다.
ini
[packages]
ENABLED = true
; 패키지 저장 경로를 별도 드라이브(예: D드라이브)로 빼고 싶다면 아래 주석을 풀고 경로 지정
; PATH = D:/gitea-packages
코드를 사용할 때는 주의가 필요합니다.
• 설정을 저장한 뒤 Windows 서비스(services.msc)에서 gitea 서비스를 재시작하거나, 실행 중인 Gitea 콘솔 창을 껐다 다시 켭니다.
• 브라우저로 http://10.0.0.1:3000에 접속했을 때, 상단 메뉴나 조직/사용자 프로필 탭에 [패키지(Packages)] 메뉴가 보이면 성공입니다.

# 2단계: Gitea 토큰 발급 및 조직(Organization) 준비

10명이 함께 쓰므로 개인 계정보다는 사내 공용 조직(예: dev-team 또는 company)을 하나 만들어 그 아래로 패키지를 모으는 것이 깔끔합니다.
1. Gitea 우측 상단 프로필 아이콘 클릭 ➡️ [설정(Settings)] ➡️ [애플리케이션(Applications)] 이동
2. 새 토큰 생성: 이름을 적고(예: package-admin), 권한 중 write:package (패키지 쓰기/읽기) 권한을 체크하여 토큰을 발급받습니다. (생성된 토큰 문자열을 복사해 두세요.)


# 3단계: Python (.whl) 패키지 올리고 설치하기


① 패키지 일괄 업로드 (관리자 PC에서 실행)

반입해 온 .whl 파일들이 모여 있는 폴더에서 PowerShell이나 CMD를 열고 twine으로 한 번에 밀어 넣습니다.
powershell
# 1. twine이 없다면 미리 반입해서 설치되어 있어야 함
# 2. 일괄 업로드 명령어 (조직명과 토큰을 본인 환경에 맞게 수정)
twine upload --repository-url http://10.0.0 -u Gitea아이디 -p 발급받은토큰 *.whl
코드를 사용할 때는 주의가 필요합니다.
• 팁: 이미 올라간 동일 버전 파일 때문에 에러가 나면서 멈추는 것을 방지하려면 --skip-existing 옵션을 뒤에 붙여주세요.

② 개발자 PC에서 설치하기 (pip.ini 설정)

개발자 10명의 PC에서 매번 긴 주소를 치지 않도록 설정 파일을 한 번만 만들어 줍니다.
• 경로: C:\Users\사용자명\AppData\Roaming\pip\pip.ini (폴더가 없으면 생성)
• 내용:ini
[global]
index-url = http://10.0.0
trusted-host = 10.0.0.1
코드를 사용할 때는 주의가 필요합니다.
• 참고: http 환경이므로 trusted-host = 10.0.0.1 설정이 반드시 들어가야 SSL 보안 경고를 피할 수 있습니다.
• 이후 개발자들은 평소처럼 pip install pandas만 치면 사내 Gitea에서 알아서 의존성까지 다 받아 설치합니다.

# 4단계: Node.js (.tgz) 패키지 올리고 설치하기


① .tgz 파일 추출 및 일괄 업로드 (관리자 PC에서 실행)

외부 인터넷 PC에서 npm install을 한 번 돌린 뒤, 캐시 폴더(%LocalAppData%\npm-cache\_cacache 등)에서 .tgz 파일을 모으거나 npm pack 패키지명으로 추출한 파일들을 준비합니다.
PowerShell에서 .tgz 파일들이 있는 폴더로 이동한 뒤 아래 명령어로 일괄 업로드합니다.
powershell
# 1. 현재 PowerShell 세션에 Gitea 인증 정보 등록
npm config set //10.0.0.1:3000/api/packages/조직명/npm/:_authToken="발급받은토큰"

# 2. 폴더 안의 모든 .tgz 파일을 반복문으로 한 번에 업로드
Get-ChildItem *.tgz | ForEach-Object { npm publish $_.Name --registry=http://10.0.0 }
코드를 사용할 때는 주의가 필요합니다.

② 개발자 PC에서 설치하기 (.npmrc 설정)

개발자 10명의 PC 사용자 폴더(C:\Users\사용자명\.npmrc)에 아래 두 줄만 넣어둡니다. (비공개 조직이라면 토큰 줄도 함께 넣어줍니다.)
ini
registry=http://10.0.0
//10.0.0.1:3000/api/packages/조직명/npm/:_authToken=발급받은토큰
코드를 사용할 때는 주의가 필요합니다.
• 이후 개발자들은 평소처럼 npm install axios나 npm install을 실행하면 사내 Gitea에서 자동으로 패키지를 내려받습니다.
