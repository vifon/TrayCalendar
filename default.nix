{ stdenv, python3, gtk3, gobject-introspection, wrapGAppsHook, ... }:

stdenv.mkDerivation rec {
  pname = "TrayCalendar";
  version = "0.9";
  src = ./traycalendar.py;

  buildInputs = [
    (python3.withPackages (pyPkgs: with pyPkgs; [
      pygobject3
    ]))
    gtk3
    gobject-introspection
  ];
  nativeBuildInputs = [ wrapGAppsHook ];

  dontUnpack = true;
  installPhase = "install -m755 -D $src $out/bin/traycalendar";
}
