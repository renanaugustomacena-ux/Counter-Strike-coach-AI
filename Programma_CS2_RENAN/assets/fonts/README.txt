Variable fonts for the Neo-tactical noir display stack.

Drop the official release TTFs here:

  SpaceGrotesk-Variable.ttf
    https://github.com/floriankarsten/space-grotesk/releases  (OFL 1.1)

  Inter-Variable.ttf  (or InterVariable.ttf from rsms)
    https://rsms.me/inter/font-files/InterVariable.ttf  (OFL 1.1)

The theme engine auto-scans this folder at startup. Without the files the
QSS falls back to Roboto (already shipped under PHOTO_GUI/). Either way
the app renders correctly; the fonts just elevate the display hierarchy.
