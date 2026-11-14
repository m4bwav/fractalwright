# fractalwright wiki verification, 0.2.0. Run from an empty folder; FW points at the clone's fw.py.
export FW_COMFY_HOSTS=""
FW="python ${FW_REPO:-D:/m4bwa/Claude/Projects/Ai/fractalwright}/scripts/fw.py"
c(){ echo "== $*"; $FW "$@" 2>&1; echo "exit: $?"; }
python -c "import numpy as n,wave;r=22050;t=n.arange(r*2)/r;s=(0.4*n.sin(2*n.pi*55*t)*(1+n.sign(n.sin(2*n.pi*2*t)))/2*32767).astype('<i2');w=wave.open('song.wav','wb');w.setnchannels(1);w.setsampwidth(2);w.setframerate(r);w.writeframes(s.tobytes())"
c --version
c doctor
c explain julia
c explain mandelbrot
c render kronecker-carpet -o carpet.png
c measure box carpet.png
c measure ifs --ratios 0.5,0.5,0.5
c measure area --size 512
c render seahorse -o seahorse.png --size 320x180
c render deep.json -o deep.png --size 160x90 --deep
c render julia-rabbit -o rabbit_b.png --size 160x90 --route browser
c palette
c palette fire -o fire.png
c sheet julia-rabbit --palettes classic,fire,ocean -o sheet.png --tile 120x68
c zoom seahorse --to-width 0.001 -o zoom.mp4 --size 160x90 --fps 12 --duration 1
c morph julia-rabbit --path "-0.12,0.75;-0.8,0.156" -o morph.mp4 --size 160x90 --fps 12 --duration 1
c loop julia-rabbit --circle 0,0,0.7885 -o loop.mp4 --size 160x90 --fps 12 --duration 1 --no-ai
c flashcheck zoom.mp4
c export "#f=mandelbrot&cx=-0.75&cy=0&w=3&it=200" -o shared.json
c audio song.wav -o song.mp4 --size 160x90 --fps 12 --duration 2 --route numpy --no-ai
c flame sierpinski -o flame.png
c lsystem koch -o koch.png --n 4
c attractor clifford -o clifford.png
c ifs fern -o fern.png
c attractor-search --hits 2 -o best.png
c fif --points "0,0;1,1;2,0" --d 0.5,-0.5 -o fif.png
c terrain -o terrain.png
c measure box koch.png
c identify --c -0.12,0.75
c 3d render mandelbulb -o bulb.png
c rd coral -o coral.png
c ca 90 -o rule90.png
c tiling penrose -o penrose.png
c kleinian apollonian -o gasket.png
c measure box penrose.png
