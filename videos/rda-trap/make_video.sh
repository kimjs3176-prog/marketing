#!/usr/bin/env bash
# Mixes narration + BGM and muxes it with the rendered frames into output/rda_trap_keynote.mp4.
# Usage: ./make_video.sh            (after rendering frames, see README)
#        ./make_video.sh --tts      (regenerate narration from audio/narration/lines.txt first)
set -euo pipefail
cd "$(dirname "$0")"

# narration start times (s) — keep in sync with the scene timings in build_scene.py
STARTS=(1.0 6.4 13.0 18.9 27.9 39.4 47.0)

if [[ "${1:-}" == "--tts" ]]; then
  while IFS='|' read -r id txt; do
    uvx edge-tts --voice ko-KR-SunHiNeural --rate=+5% --text "$txt" --write-media "audio/narration/$id.mp3" >/dev/null
    ffmpeg -v error -y -i "audio/narration/$id.mp3" \
      -af "silenceremove=start_periods=1:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse" \
      -ar 48000 "audio/narration/$id.wav"
    rm "audio/narration/$id.mp3"
  done < audio/narration/lines.txt
fi

inputs=(-i audio/bgm.mp3)
delays=""
labels=""
for i in "${!STARTS[@]}"; do
  n=$((i + 1))
  inputs+=(-i "audio/narration/n$n.wav")
  ms=$(awk "BEGIN{print int(${STARTS[$i]}*1000)}")
  delays+="[$n]adelay=$ms:all=1[a$n];"
  labels+="[a$n]"
done
k=${#STARTS[@]}
inputs+=(-i audio/shutter.wav -i audio/shutter.wav)

ffmpeg -v error -y "${inputs[@]}" -filter_complex "\
[0]aresample=48000,apad=whole_dur=61,volume=0.42,afade=t=in:d=1.5,afade=t=out:st=57.8:d=3.2[bgm];\
${delays}${labels}amix=inputs=$k:normalize=0,pan=stereo|c0=c0|c1=c0,apad=whole_dur=61,asplit[nar][sc];\
[bgm][sc]sidechaincompress=threshold=0.03:ratio=6:attack=40:release=500[duck];\
[$((k + 1))]adelay=36000:all=1,volume=0.5[s1];[$((k + 2))]adelay=37200:all=1,volume=0.5[s2];\
[duck][nar][s1][s2]amix=inputs=4:normalize=0,atrim=0:61,loudnorm=I=-16:TP=-1.5:LRA=11" \
  -ar 48000 audio/mix.wav

mkdir -p output
ffmpeg -v error -y -framerate 24 -i frames/f_%04d.png -i audio/mix.wav \
  -c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p -c:a aac -b:a 192k -shortest -movflags +faststart \
  output/rda_trap_keynote.mp4
echo "wrote output/rda_trap_keynote.mp4"
