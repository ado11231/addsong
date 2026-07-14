# bash completion for addsong
#
# Install by sourcing from ~/.bashrc
#     source /path/to/completions/addsong.bash
# or drop into your bash completion directory. Homebrew installs it there
# automatically. See README Shell completions for details.

_addsong() {
  local cur prev
  cur="${COMP_WORDS[COMP_CWORD]}"
  prev="${COMP_WORDS[COMP_CWORD-1]}"

  local subcommands="subscribe unsubscribe list sync forget"
  local opts="--playlist --from --results --format --quality -y --yes --review \
--reimport -n --dry-run -q --quiet -v --verbose --no-color --notify --no-progress \
-h --help --version"

  # Complete the argument after an option that takes a value.
  case "$prev" in
    --format)
      # shellcheck disable=SC2207
      COMPREPLY=( $(compgen -W "m4a mp3 flac opus vorbis wav aac alac best" -- "$cur") )
      return ;;
    --quality)
      # shellcheck disable=SC2207
      COMPREPLY=( $(compgen -W "0 1 2 3 4 5 6 7 8 9 10" -- "$cur") )
      return ;;
    --from)
      # shellcheck disable=SC2207
      COMPREPLY=( $(compgen -f -- "$cur") )
      return ;;
    --results)
      return ;;   # expects a number, nothing to complete
  esac

  # First word can be a subcommand or option. After that only options complete.
  if [[ "$COMP_CWORD" -eq 1 ]]; then
    # shellcheck disable=SC2207
    COMPREPLY=( $(compgen -W "$subcommands $opts" -- "$cur") )
  elif [[ "$cur" == -* ]]; then
    # shellcheck disable=SC2207
    COMPREPLY=( $(compgen -W "$opts" -- "$cur") )
  fi
}

complete -F _addsong addsong
