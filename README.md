# 상세페이지 전문가 업그레이드

상세페이지 자동화 GUI의 전문가 업그레이드 작업 원본입니다.

포함 항목:

- `expert-upgrade/`: EXE에 반영하는 빌드 스크립트, 상세페이지/마켓 프롬프트, 검증 스크립트
- `source-recovery/`: 빌드 기준이 되는 GUI 소스
- `tools/`: EXE 아카이브 패치와 섹션·이미지 프롬프트 보조 코드
- `known-good-release/`: 검증한 기존 GUI 기준본 EXE와 브랜드 로고, 섹션별 추가 프롬프트 템플릿, 저장된 추가 프롬프트 예시를 모은 배포 묶음. 최근 플러그인 진단용 후보는 제외합니다.

## EXE 빌드

원본 EXE는 GitHub 일반 파일 제한을 넘으므로 저장소에는 넣지 않았습니다. 원본 EXE를 바탕화면에 둔 뒤, Windows와 Python 3.11 환경에서 다음 명령으로 별도 대상 파일을 만듭니다.

```powershell
$env:EXPERT_PREVIEW_EXE = "$env:USERPROFILE\Desktop\상세페이지 전문가 업그레이드 - 배포용.exe"
python .\expert-upgrade\build_upgrade.py
```

생성 파일은 원본 EXE를 변경하지 않습니다. Chrome 또는 Edge와 ChatGPT 로그인은 실행하는 PC마다 필요합니다.

기준본 EXE와 동봉 자료는 [`known-good-release/README.md`](known-good-release/README.md)를 확인하세요. EXE는 GitHub 용량 제한을 고려해 Git LFS로 관리합니다.
