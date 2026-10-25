# 기술소개영상 — 장기간 유인 및 살충이 가능한 트랩

농촌진흥청 특허 제10-3014127호(출원인: 대한민국(농촌진흥청장), 주식회사 비온디솔루션) 기술소개영상.
애플 키노트 스타일, 61초, 1920×1080 · 24fps. 완성본: [`output/rda_trap_keynote.mp4`](output/rda_trap_keynote.mp4)

장면 구성과 내레이션은 [`scenario.md`](scenario.md) 참고.

## 구성

| 파일 | 내용 |
|---|---|
| `build_scene.py` | Blender 씬 생성 스크립트 (트랩 3D 모델, 타이포, 카메라·애니메이션 전부) |
| `trap_keynote.blend` | 위 스크립트로 생성된 Blender 파일 |
| `audio/narration/lines.txt` | 내레이션 대본 (`id|문장`) |
| `audio/narration/n*.wav` | 여성 음성(ko-KR-SunHiNeural) 내레이션 |
| `audio/bgm.mp3` | 배경음악 「밝은 미래의 시작」 (Suno 생성) |
| `audio/shutter.wav` | 카메라 플래시 효과음 |
| `subtitles.srt` | 자막 (영상에 미삽입, 별도 파일) |
| `make_video.sh` | 오디오 믹스 + 프레임 합성 → mp4 |

렌더 프레임(`frames/`, 약 2GB)은 저장소에 넣지 않습니다.

## 다시 만들기

필요: Blender 5.2, ffmpeg, uv(내레이션 재생성 시), 나눔스퀘어 네오 폰트(사용자 폰트 폴더에 설치).

```bash
# 1) 씬 생성 (build_scene.py 수정 후)
blender -b --factory-startup -noaudio --python build_scene.py

# 2) 렌더 — 전체 약 50분(Iris Xe 기준), 바뀐 구간만 렌더하려면 -s/-e 지정
blender -b trap_keynote.blend -noaudio -a                 # 전체
blender -b trap_keynote.blend -noaudio -s 1 -e 145 -a     # 예: 인트로(0–6초)만

# 3) 오디오 믹스 + mp4
./make_video.sh          # 대본을 바꿨다면 ./make_video.sh --tts
```

- 프레임 번호 = 초 × 24 + 1
- 렌더 중에는 Blender GUI를 닫아 두는 것이 빠릅니다
- 내레이션 시작 시각은 `make_video.sh`의 `STARTS`에서 조정
