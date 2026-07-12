FROM python:3.13-slim

# Runtime X11 stack + build toolchain + GUI backends + a tiny window manager.
# Linux findings baked in:
#  #1  pynput -> evdev is a C ext on Linux: needs gcc + linux-libc-dev.
#  #2  pyautogui -> mouseinfo needs tkinter (python3-tk) on Linux.
#  #3  pyscreeze screenshots need XDG_SESSION_TYPE=x11 (env) so it uses scrot.
#  #4  keystrokes need a WM for window focus; openbox is a ~1MB minimal WM.
RUN apt-get update && apt-get install -y --no-install-recommends \
        xvfb x11-utils x11-xserver-utils xauth \
        scrot xterm xdotool wmctrl openbox \
        libx11-6 libxext6 libxtst6 libxrender1 libxi6 \
        python3-tk \
        procps ca-certificates \
        gcc build-essential linux-libc-dev python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Pure-python SDK path only. NO hai-agent-runtime binary anywhere.
RUN pip install --no-cache-dir "hai-agents[desktop]"
RUN echo "which hai-agent-runtime:" && (which hai-agent-runtime || echo "ABSENT (as intended)")

WORKDIR /work
ENV DISPLAY=:99 XDG_SESSION_TYPE=x11
CMD ["/bin/bash"]
