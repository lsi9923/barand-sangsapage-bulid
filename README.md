# 상세페이지 전문가 업그레이드

상세페이지 자동화 GUI의 전문가 업그레이드 작업 원본입니다.

포함 항목:

- `expert-upgrade/`: EXE에 반영하는 빌드 스크립트, 상세페이지/마켓 프롬프트, 검증 스크립트
- `source-recovery/`: 빌드 기준이 되는 GUI 소스
- `tools/`: EXE 아카이브 패치와 섹션·이미지 프롬프트 보조 코드

## EXE 빌드

원본 EXE는 GitHub 일반 파일 제한을 넘으므로 저장소에는 넣지 않았습니다. 원본 EXE를 바탕화면에 둔 뒤, Windows와 Python 3.11 환경에서 다음 명령으로 별도 대상 파일을 만듭니다.

```powershell
$env:EXPERT_PREVIEW_EXE = "$env:USERPROFILE\Desktop\상세페이지 전문가 업그레이드 - 배포용.exe"
python .\expert-upgrade\build_upgrade.py
```

생성 파일은 원본 EXE를 변경하지 않습니다. Chrome 또는 Edge와 ChatGPT 로그인은 실행하는 PC마다 필요합니다.

## 렌더 실패 및 공급처 URL 보강

기존 같은탭·썸네일보강·작업제어 EXE를 바탕으로 렌더 연결 수명과 업체별 이미지 수집 제한을 보강할 수 있습니다. 원본과 현재 실행 중인 EXE는 변경하지 않습니다.

```powershell
python -m tools.patch_render_resilience_exe `
  "$env:USERPROFILE\Desktop\상세페이지 자동화 GUI - 같은탭_썸네일보강_작업제어.exe" `
  "$env:USERPROFILE\Desktop\상세페이지 자동화 GUI - 같은탭_렌더보강_v2.exe"
```

보강 대상은 닫힌 브라우저 페이지 재사용 차단, ChatGPT `Event loop is closed` 1회 재연결, 공급처·도매·소싱 URL 헤더 인식, 특정 도메인에 종속되지 않는 기본·보조 상품 이미지 수집입니다. 기존 섹션·썸네일·로고·마켓 등록 로직은 패처에서 변경하지 않습니다.
