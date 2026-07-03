. "$HOME/.profile"

case ":$PATH:" in
  *:"$HOME/.local/share/mise/shims":*) ;;
  *) export PATH="$HOME/.local/share/mise/shims:$PATH" ;;
esac

[[ -f "$HOME/.cargo/env" ]] && source "$HOME/.cargo/env"
