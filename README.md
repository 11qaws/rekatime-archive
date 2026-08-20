# rekatime-archive

유레카 노래방송 아카이브. [rekatime](https://github.com/11qaws) 의 분석 결과를 읽어 정적 페이지로 굽습니다.

## 화면

| 주소 | 답하는 질문 |
|---|---|
| `/` | 최근 방송 — 대표 장면과 셋리스트 |
| `/main.html?broadcast=<session_id>` | 선택한 방송을 최근 방송 프레임에서 보기 |
| `/archive.html` | 월간 방송 목록과 월간 흐름 |
| `/song.html` | 노래 카드 검색과 개별 노래 기록 |
| `/stats.html` | 방송을 겹쳐야 보이는 것 |

운영 주소는 Cloudflare Pages의 `https://rekatime.pages.dev`를 사용합니다.

## 만들어지는 방식

수집·분석(YAMNet · inaSpeechSegmenter · OCR)과 페이지 굽기는 로컬에서 돕니다.
원본 영상과 GPU가 필요해 러너에서 돌릴 수 없습니다. 이 저장소에는 결과물만 올라옵니다.

```
python scripts/export_pages.py --thumb-mode path   # 데이터
python artifacts/build_pages.py --pages            # 페이지
```

## 자동으로 도는 것

`.github/workflows/refresh-hls.yml` 하나뿐입니다. 소리만 듣기에 쓰는 치지직 HLS 주소가
약 17시간 뒤 만료되므로 12시간마다 `hls.json` 만 다시 씁니다.
페이지는 이 파일을 먼저 읽고, 없거나 실패하면 구울 때 박힌 주소로 되돌아갑니다.

## 데이터

곡 정보는 setlink.jp 노래책(949곡)을, 타임스탬프는 rekatime 의 분석 결과를 씁니다.
제목이 노래책과 맞지 않는 곡은 집계에서 빼고 통계 페이지에 따로 보여 줍니다 —
고치는 일은 rekatime 쪽에서 합니다.
