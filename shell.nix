{ ... }:
let
  nixpkgs = builtins.fetchTarball {
    name   = "nixpkgs-unstable-2022-03-25";
    url    = "https://github.com/NixOS/nixpkgs/archive/1d08ea2bd83abef174fb43cbfb8a856b8ef2ce26.tar.gz";
    sha256 = "1q8p2bz7i620ilnmnnyj9hgx71rd2j6sjza0s0w1wibzr9bx0z05";
  };
  rust-overlay = builtins.fetchTarball {
    name   = "rust-overlay-2022-03-09";
    url    = "https://github.com/oxalica/rust-overlay/archive/7f599870402c8d2a5806086c8ee0f2d92b175c54.tar.gz";
    sha256 = "1dhwih79qndb19j58xnw4gx2340xxqkp0nrnjm674hl8h9fc5nnr";
  };

  overlays = [
    (import rust-overlay)
  ];
  pkgs = import nixpkgs { overlays = overlays; };

  rustenv = pkgs.rust-bin.selectLatestNightlyWith (toolchain: toolchain.minimal.override {
    targets = [ "aarch64-unknown-none-softfloat" ];
  });
in
pkgs.mkShell {
  nativeBuildInputs = with pkgs; [
    bashInteractive
    dtc
    imagemagick
    pkgsCross.aarch64-multiplatform.buildPackages.gcc
    rustenv
    p7zip
    cpio
  ];

  ARCH = "aarch64-unknown-linux-gnu-";

  NIXOS_ICONS_ICNS = pkgs.runCommand "nixos-icons.icns" {
    nativeBuildInputs = with pkgs; [
      imagemagick
      libicns
    ];
  } ''
    mkdir tmp

    # ICNS icons must be square. Adds transparent padding
    for size in "16x16" "32x32" "48x48" "128x128" "256x256" "512x512" "1024x1024"; do
      convert -background none -gravity center "${pkgs.nixos-icons}/share/icons/hicolor/$size/apps/nix-snowflake.png" -resize $size -extent $size tmp/$size.png
    done

    png2icns $out tmp/*.png
  '';
}
