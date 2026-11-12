"""Validate the content library: python -m hebbot.validate"""
import sys

from hebbot import content as content_lib


def main():
    content = content_lib.load_content()
    errors = content_lib.validate(content)
    n_words = sum(len(t["words"]) for t in content["themes"].values())
    n_root_words = sum(len(r["words"]) for r in content["roots"])
    drafts = [t for t in content["themes"].values() if t.get("status") == "draft"]
    drafts += [r for r in content["roots"] if r.get("status") == "draft"]
    print(f"{len(content['themes'])} themes ({n_words} words), "
          f"{len(content['roots'])} roots ({n_root_words} words), {len(drafts)} sets still in draft")
    if errors:
        print(f"\n{len(errors)} problem(s):")
        for e in errors:
            print(f" - {e}")
        sys.exit(1)
    print("Content is valid.")


if __name__ == "__main__":
    main()
