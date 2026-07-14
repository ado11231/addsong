# Homebrew formula for addsong.
#
# This file is ready to drop into a personal "tap" repository so users can run:
#
#     brew install ado11231/tap/addsong
#
# A tap is just a GitHub repo named `homebrew-tap` with a `Formula/` directory;
# one tap can hold the formulae for all of your tools. See RELEASE.md for the
# exact steps to publish (tag the release, fill in the sha256, create the tap).
#
# Before publishing, set the sha256 to the checksum of the release tarball
# (RELEASE.md shows how).
class Addsong < Formula
  include Language::Python::Virtualenv

  desc "Download a song from a URL and auto-import it into Apple Music"
  homepage "https://github.com/ado11231/apple-music-pipeline"
  url "https://github.com/ado11231/apple-music-pipeline/archive/refs/tags/v1.0.0.tar.gz"
  sha256 "0000000000000000000000000000000000000000000000000000000000000000"
  license "MIT"

  depends_on "python@3.12"
  depends_on "ffmpeg"
  depends_on :macOS # addsong writes into Apple Music's watch folder
  depends_on "yt-dlp"

  resource("rich") do
    url "https://files.pythonhosted.org/packages/source/r/rich/rich-13.7.0.tar.gz"
    sha256 "0000000000000000000000000000000000000000000000000000000000000000"
  end

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "addsong #{version}", shell_output("#{bin}/addsong --version")
  end
end