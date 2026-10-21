"""Small command line front end with a mandatory approval prompt."""
import sys
import uuid

from langgraph.types import Command

from .engine import make_engine


def run(engine, text: str, thread_id: str):
    cfg = {"configurable": {"thread_id": thread_id}}
    out = engine.invoke({"user_input": text}, cfg)
    while "__interrupt__" in out:
        info = out["__interrupt__"][0].value
        if info["type"] == "followup":
            print(f"\n{info['message']}")
            answer = input("What next? (e.g. 'fix it', or Enter to stop): ")
        else:
            print(f"\nAPPROVAL NEEDED [{info['plugin']}]: {info['action']}")
            if info.get("explanation"):
                print("  why:", info["explanation"])
            answer = input("Approve? (y/n): ")
        out = engine.invoke(Command(resume=answer), cfg)
    print("\n" + out.get("final", ""))


def main():
    engine = make_engine({"github"})
    thread = str(uuid.uuid4())
    text = " ".join(sys.argv[1:]) or input("Describe the problem: ")
    run(engine, text, thread)


if __name__ == "__main__":
    main()
