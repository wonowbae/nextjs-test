1. 깨끗한 환경 생성 (폐쇄망)
conda create -n clean --offline python=3.11 matplotlib numpy


이 명령어는 다음과 같이 동작해.
- base에 추가로 설치했던 패키지들은 복제하지 않음.
- Python 3.11, Matplotlib, NumPy 및 필수 의존성만 설치.
- 로컬 Conda 패키지 캐시만 사용.
- 인터넷 접속은 시도하지 않음.
단, 필요한 패키지와 호환되는 버전이 로컬 캐시에 있어야 해.
2. Anaconda 최초 설치 상태를 그대로 원한다면?
여기서 한 가지 차이가 있어.
- Conda 환경: 기본적으로 Python과 지정한 패키지만 설치.
- Anaconda 배포판: 최초 설치 시 Matplotlib, NumPy, Pandas, SciPy 등 다양한 라이브러리가 포함됨.
즉, 위 명령어는 Anaconda 최초 설치 상태를 재현하는 게 아니라, 필요한 패키지만 설치하는 방식이야.

Anaconda 최초 설치 시의 패키지 구성을 정확하게 재현하려면 별도의 초기 패키지 목록이 필요해.
3. 확인
conda activate clean
conda list


Matplotlib가 정상적으로 설치됐는지도 확인해 봐.
python -c "import matplotlib; print(matplotlib.__version__)"
