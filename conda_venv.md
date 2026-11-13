Conda에서 base 대신 새로운 가상환경을 만들려면 다음 명령어를 사용하면 돼.
1. 새 가상환경 생성
conda create -n myenv python=3.11


- -n myenv: 가상환경 이름
- python=3.11: 사용할 Python 버전
2. 가상환경 활성화
conda activate myenv


프롬프트가 (base)에서 (myenv)로 바뀌면 성공이야.
3. 패키지 설치
conda install matplotlib numpy


또는 pip로 설치할 수도 있어.
python -m pip install matplotlib


4. 가상환경 관리
명령어	설명
conda env list	모든 가상환경 조회
conda deactivate	현재 환경 비활성화
conda remove -n myenv --all	가상환경 삭제
conda list	현재 환경의 패키지 조회

5. 터미널 실행 시 base 자동 활성화 방지
conda config --set auto_activate_base false


이렇게 하면 터미널을 열 때마다 (base)가 자동으로 활성화되지 않아.

참고: 지금처럼 폐쇄망에서 작업한다면, Anaconda 설치 시 제공된 패키지만 사용해서 환경을 만들 수도 있어.
conda create -n myenv python=3.11 --offline
