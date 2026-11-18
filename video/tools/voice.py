"""One continuous Andrew take for the whole script, with word timings.
Writes public/vo/full.mp3 and src/voice.json: [{scene, start, end, words:[[start, end, text]]}] in seconds."""
import asyncio, json, edge_tts

VOICE, RATE = "en-US-AndrewNeural", "+6%"
script = json.load(open("script.json"))

async def main():
    text = " ".join(s["text"] for s in script)
    com = edge_tts.Communicate(text, VOICE, rate=RATE, boundary="WordBoundary")
    words = []
    with open("public/vo/full.mp3", "wb") as f:
        async for chunk in com.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                s = chunk["offset"] / 1e7
                words.append([round(s, 3), round(s + chunk["duration"] / 1e7, 3), chunk["text"]])
    # find where each scene starts: the first spot matching its opening two words, in order
    norm = lambda w: "".join(c for c in w.lower().replace("\u2019", "'") if c.isalnum())
    starts, i = [], 0
    for s in script:
        a, b = [norm(w) for w in s["text"].split()[:2]]
        while not (norm(words[i][2]) == a and norm(words[i + 1][2]) == b):
            i += 1
        starts.append(i)
        i += 1
    starts.append(len(words))
    out = []
    for k, s in enumerate(script):
        ws = words[starts[k]:starts[k + 1]]
        out.append({"scene": s["id"], "start": ws[0][0], "end": ws[-1][1], "words": ws})
    json.dump(out, open("src/voice.json", "w"), indent=1)
    for o in out:
        print(o["scene"], o["start"], o["end"], " ".join(w[2] for w in o["words"][:4]), "...")

def edge_tts_words(t):
    # the service reports punctuation-free tokens split on spaces; dashes stay inside words
    return [w for w in t.replace("’", "'").split() if any(c.isalnum() for c in w)]

asyncio.run(main())
