import os
import glob
import shutil
import subprocess
import tempfile
import requests

# ==========================================
# 1. Gitea 서버 및 인증 정보 설정 (본인 환경에 맞게 수정)
# ==========================================
GITEA_HOST = "http://10.0.0.1:3000"
ORG_NAME = "조직명"
USERNAME = "Gitea아이디"
TOKEN = "발급받은토큰"

PYPI_URL = f"{GITEA_HOST}/api/packages/{ORG_NAME}/pypi"
NPM_URL = f"{GITEA_HOST}/api/packages/{ORG_NAME}/npm/"


def upload_whl_files():
    """현재 폴더의 모든 .whl 파일을 Gitea PyPI 레지스트리에 업로드"""
    whl_files = glob.glob("*.whl")
    if not whl_files:
        return

    print(f"\n=== Python (.whl) 패키지 {len(whl_files)}개 업로드 시작 ===")
    for filepath in whl_files:
        filename = os.path.basename(filepath)
        with open(filepath, "rb") as f:
            files = {"content": (filename, f, "application/octet-stream")}
            data = {":action": "file_upload"}
            try:
                res = requests.post(
                    PYPI_URL,
                    auth=(USERNAME, TOKEN),
                    data=data,
                    files=files,
                    timeout=30,
                )
                if res.status_code in (200, 201):
                    print(f"[성공] {filename}")
                elif res.status_code == 400 and "already exists" in res.text:
                    print(f"[스킵] {filename} (이미 존재함)")
                else:
                    print(f"[실패] {filename} -> 상태코드: {res.status_code}, {res.text}")
            except Exception as e:
                print(f"[에러] {filename} -> {e}")


def find_all_npm_packages(base_dir="node_modules"):
    """중첩된 node_modules 내부까지 탐색하여 모든 유효한 패키지 경로를 반환"""
    package_dirs = []
    if not os.path.exists(base_dir):
        return package_dirs

    for root, dirs, files in os.walk(base_dir):
        # .bin 등 숨김 폴더 제외
        dirs[:] = [d for d in dirs if not d.startswith(".")]

        # package.json이 있는 폴더면 실제 npm 패키지로 간주
        if "package.json" in files:
            # 루트 프로젝트 자체는 제외하고 node_modules 하위의 패키지만 수집
            if "node_modules" in root.split(os.sep):
                package_dirs.append(root)

    return package_dirs


def upload_node_modules():
    """node_modules 내 모든 패키지를 .tgz로 압축 후 Gitea npm 레지스트리에 업로드"""
    pkg_dirs = find_all_npm_packages("node_modules")
    if not pkg_dirs:
        return

    print(f"\n=== Node.js 패키지 {len(pkg_dirs)}개 추출 및 업로드 시작 ===")

    # 임시 폴더 생성 (작업 후 자동 삭제)
    temp_dir = tempfile.mkdtemp(prefix="gitea_npm_")
    npm_cmd = "npm.cmd" if os.name == "nt" else "npm"

    # 인증 토큰 설정
    auth_host = GITEA_HOST.replace("http://", "").replace("https://", "")
    subprocess.run(
        [npm_cmd, "config", "set", f"//{auth_host}/api/packages/{ORG_NAME}/npm/:_authToken={TOKEN}"],
        check=False,
        stdout=subprocess.DEVNULL,
    )

    try:
        # 1. 모든 패키지를 임시 폴더에 .tgz로 압축
        for idx, pkg_path in enumerate(pkg_dirs, 1):
            abs_pkg_path = os.path.abspath(pkg_path)
            print(f"[{idx}/{len(pkg_dirs)}] 압축 중: {pkg_path}")
            subprocess.run(
                [npm_cmd, "pack", abs_pkg_path, "--silent"],
                cwd=temp_dir,
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

        # 2. 생성된 .tgz 파일들을 일괄 업로드
        tgz_files = glob.glob(os.path.join(temp_dir, "*.tgz"))
        print(f"\n총 {len(tgz_files)}개의 .tgz 파일 Gitea 업로드 시작...")

        for tgz_path in tgz_files:
            tgz_name = os.path.basename(tgz_path)
            res = subprocess.run(
                [npm_cmd, "publish", tgz_path, f"--registry={NPM_URL}"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            if res.returncode == 0:
                print(f"[성공] {tgz_name}")
            elif "409" in res.stderr or "already exists" in res.stderr or "cannot publish over" in res.stderr:
                print(f"[스킵] {tgz_name} (이미 존재함)")
            else:
                print(f"[실패] {tgz_name} -> {res.stderr.strip().splitlines()[-1] if res.stderr else '알 수 없는 오류'}")

    finally:
        # 임시 폴더 정리
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    print("Gitea 사내 패키지 일괄 업로더를 실행합니다...")
    upload_whl_files()
    upload_node_modules()
    print("\n=== 모든 작업이 완료되었습니다 ===")
