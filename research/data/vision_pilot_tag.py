import base64, json, os, sys, time, urllib.request, glob
img_dir, out_dir = sys.argv[1], sys.argv[2]
models = sys.argv[3].split(',')
key = os.environ['OPENROUTER_API_KEY']
BOOKS = {'Ge':'Genesis','Le':'Leviticus','Ps':'Psalms','Mk':'Mark','Ac':'Acts'}
PROMPT = """You are tagging a hand-drawn Bible illustration from the Sweet Publishing "Read 'n Grow Picture Bible" (Jim Padgett).
The file name says it illustrates {book} chapter {ch} (frame {fr} of that chapter). The frame number is NOT a verse number.
Rules: describe only what is visibly drawn. Name a biblical person only if the passage makes the identity clear AND the drawing fits; otherwise use a generic label ("man on a mat"). Never invent details. Record uncertainty.
Return ONLY JSON with keys:
{{"passage_guess": "{book} {ch}:v1-v2 or null", "passage_confidence": "high|medium|low",
 "scene_summary": "one sentence",
 "people": [{{"label": "generic visual label", "identity": "biblical name or null", "identity_basis": "passage|visual|none"}}],
 "figure_count": int, "places": [], "objects": [], "actions": [], "setting": "indoor|outdoor|mixed",
 "time_of_day": "day|night|unclear", "mood": "", "uncertain": ["things you were unsure about"]}}"""
for model in models:
    for f in sorted(glob.glob(img_dir + '/*.jpg')):
        name = os.path.basename(f)[:-4]
        _, bk, ch, fr, _ = name.split('_')
        b64 = base64.b64encode(open(f, 'rb').read()).decode()
        body = {"model": model, "max_tokens": 1500,
                "messages": [{"role": "user", "content": [
                    {"type": "text", "text": PROMPT.format(book=BOOKS[bk], ch=int(ch), fr=int(fr))},
                    {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + b64}}]}],
                "usage": {"include": True}}
        req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=json.dumps(body).encode(),
              headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
        t = time.time()
        try:
            r = json.load(urllib.request.urlopen(req, timeout=180))
        except Exception as e:
            print(model, name, 'ERROR', e); continue
        u = r.get('usage', {})
        txt = r['choices'][0]['message']['content']
        rec = {"model": model, "image": name, "secs": round(time.time()-t, 1), "prompt_tokens": u.get('prompt_tokens'),
               "completion_tokens": u.get('completion_tokens'), "reasoning_tokens": (u.get('completion_tokens_details') or {}).get('reasoning_tokens'),
               "cost": u.get('cost'), "output": txt}
        with open(out_dir + '/results.jsonl', 'a') as o: o.write(json.dumps(rec) + '\n')
        print(model, name, rec['prompt_tokens'], rec['completion_tokens'], rec['reasoning_tokens'], rec['cost'], rec['secs'])
