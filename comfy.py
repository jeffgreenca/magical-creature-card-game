import requests
import json
import random
import time
import logging
import os
from collections import OrderedDict

# log time, level and message
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

workflow = json.loads("""{
  "1": {
    "inputs": {
      "ckpt_name": "juggernautXL_version5.safetensors"
    },
    "class_type": "CheckpointLoaderSimple",
    "_meta": {
      "title": "Load Checkpoint"
    }
  },
  "2": {
    "inputs": {
      "text": "dreamyvibes artstyle, a (rainbow maker:1.5), amazing, incredible, high quality, best, 8k, close focus on subject, simple background, macro photography",
      "clip": [
        "22",
        1
      ]
    },
    "class_type": "CLIPTextEncode",
    "_meta": {
      "title": "CLIP Text Encode (Prompt)"
    }
  },
  "9": {
    "inputs": {
      "text": [
        "10",
        0
      ],
      "clip": [
        "22",
        1
      ]
    },
    "class_type": "CLIPTextEncode",
    "_meta": {
      "title": "CLIP Text Encode (Prompt)"
    }
  },
  "10": {
    "inputs": {
      "strings": "deformed, lowres, bad quality, text, watermark, scary, nsfw, sexy, violent, landscape",
      "multiline": true,
      "select": 0
    },
    "class_type": "ImpactStringSelector",
    "_meta": {
      "title": "String Selector"
    }
  },
  "11": {
    "inputs": {
      "seed": 512439326012741,
      "steps": 30,
      "cfg": 6,
      "sampler_name": "dpmpp_2m",
      "scheduler": "karras",
      "denoise": 1,
      "model": [
        "22",
        0
      ],
      "positive": [
        "2",
        0
      ],
      "negative": [
        "9",
        0
      ],
      "latent_image": [
        "12",
        0
      ]
    },
    "class_type": "KSampler",
    "_meta": {
      "title": "KSampler"
    }
  },
  "12": {
    "inputs": {
      "width": 1344,
      "height": 768,
      "batch_size": 1
    },
    "class_type": "EmptyLatentImage",
    "_meta": {
      "title": "Empty Latent Image"
    }
  },
  "15": {
    "inputs": {
      "samples": [
        "11",
        0
      ],
      "vae": [
        "1",
        2
      ]
    },
    "class_type": "VAEDecode",
    "_meta": {
      "title": "VAE Decode"
    }
  },
  "18": {
    "inputs": {
      "images": [
        "15",
        0
      ]
    },
    "class_type": "PreviewImage",
    "_meta": {
      "title": "Preview Image"
    }
  },
  "19": {
    "inputs": {
      "filename_prefix": "ComfyUI",
      "images": [
        "15",
        0
      ]
    },
    "class_type": "SaveImage",
    "_meta": {
      "title": "Save Image"
    }
  },
  "22": {
    "inputs": {
      "lora_name": "Dreamyvibes artstyle SDXL - Trigger with dreamyvibes artstyle.safetensors",
      "strength_model": 0.85,
      "strength_clip": 0.85,
      "model": [
        "1",
        0
      ],
      "clip": [
        "1",
        1
      ]
    },
    "class_type": "LoraLoader",
    "_meta": {
      "title": "Load LoRA"
    }
  }
}
""")

COMFY_URL = "http://127.0.0.1:8188/prompt"

def check_queue_depth():
    # returns {"exec_info": {"queue_remaining": 0}}
    r = requests.get(COMFY_URL)
    r.raise_for_status()
    return r.json()["exec_info"]["queue_remaining"]

def comfy_prompt(positive_prompt, seed=None):
    if seed is None:
        seed = random.randint(0, 900000000000000)
    w = workflow.copy()
    w["2"]["inputs"]["text"] = positive_prompt
    w["11"]["inputs"]["seed"] = f"{seed}"
    r = requests.post(COMFY_URL, json={"prompt": w})
    r.raise_for_status()

def llm():
    prompt="""Make a list of Cute Animals, Magical Objects, Fairy Friends, and Whimsical Wonders. This is for a card game for kids. Each category should have at least 20 items.
    Return the list with one item per line, without any additional text. Do not state anything about the category, we don't need that in the list output. Examples:
    fawn
    unicorn
    water nymph
    tree spirit
    magic potion
    """

    OPENAI_URL = "https://api.openai.com/v1/chat/completions"
    with open(".api_key", "r") as f:
        api_key = f.read().strip()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    data = {
        "model": "gpt-4-turbo-preview",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]
    }
    r = requests.post(OPENAI_URL, headers=headers, json=data)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

def parse_words_from_llm(llm_output):
    # we need to split on \n, remove blank lines, and trim whitespace
    return [x.strip().lower() for x in llm_output.split("\n") if x.strip()]

class WordsManager:
    """Words manager maintains two text files, one for new words and one for used words. We always add new words to the end of the new words text file, and we always remove words from the beginning of the new words file and add them to the end of the used words file."""

    def __init__(self, new_words_file="words.txt", used_words_file="used_words.txt"):
        self.new_words_file = new_words_file
        self.used_words_file = used_words_file

    def _clean_words(self, words):
        return [x.strip().lower() for x in words if x.strip()]

    def add_words(self, words):
        with open(self.new_words_file, "a") as f:
            for word in self._clean_words(words):
                f.write(word + "\n")

    def pop_word(self):
        """Return an unused word (or None), and move it to the used words list."""
        if not os.path.exists(self.new_words_file):
            return None
        with open(self.new_words_file, "r") as f:
            words = f.readlines()
        if not words:
            return None
        # before we continue, take this opportunity to deduplicate
        # without changing the order
        before = len(words)
        words = list(OrderedDict.fromkeys(words))
        after = len(words)
        if before != after:
            logging.info("removed %d duplicates from words", before - after)
        word = words[0].strip()
        with open(self.new_words_file, "w") as f:
            for w in words[1:]:
                f.write(w)
        with open(self.used_words_file, "a") as f:
            f.write(word + "\n")
        return word


if __name__ == "__main__":
    wm = WordsManager()
    while True:
        try:
            word = wm.pop_word()
            if word is None:
                logging.info("No more words to process. Obtaining new words")
                n = llm()
                words = parse_words_from_llm(n)
                wm.add_words(words)
                continue

            p = f"dreamyvibes artstyle, a ({word}:1.5), amazing, incredible, high quality, best, 8k, close focus on subject, simple background, macro photography"
            while check_queue_depth() > 5:
                logging.info("queue depth: %d (waiting...)", check_queue_depth())
                time.sleep(30)
            logging.info("sending word: %s", word)
            comfy_prompt(p)
        except Exception as e:
            # check for ctrl-c
            if isinstance(e, KeyboardInterrupt):
                break
            logging.error("exception: %s", e)
            time.sleep(0.5)