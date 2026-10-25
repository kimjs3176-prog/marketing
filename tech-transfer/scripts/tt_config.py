"""공통 경로 설정. 데이터·산출물은 저장소 밖(또는 .gitignore 대상)에 둔다.

TT_DATA : 작업 데이터 폴더 (rda.json, bib.json, packets/, content/, ais/, src/ ...)
TT_OUT  : HWPX·PDF 산출 폴더 (경기A+센터/, 서울A+센터/)
KIPRIS_KEY, AIS_ANON_KEY : API 키 (환경변수로만 전달, 저장소에 넣지 않음)
"""
import os
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
DATA = Path(os.environ.get("TT_DATA", SCRIPTS.parent / "data"))
OUT = Path(os.environ.get("TT_OUT", SCRIPTS.parent / "output"))
DATA.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)
