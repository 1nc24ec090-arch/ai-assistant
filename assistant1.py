import speech_recognition as sr
import pyttsx3
import datetime
import webbrowser
import wikipedia
import requests
import os
import sys
import threading
import time
import json
from random import choice

WAKE_WORDS = ("hey assistant", "ok assistant", "assistant","voice bot")
MUSIC_FOLDER = r"C:\Users\%USERNAME%\Music"
APP_PATHS = {
    "vscode": r"C:\Users\%USERNAME%\AppData\Local\Programs\Microsoft VS Code\Code.exe",
    "calculator": r"C:\Windows\System32\calc.exe",
}
REMINDERS_FILE = "assistant_reminders.json"
SMALL_TALKS = {
    "how are you": ["I'm fine, thanks! How about you?", "Doing great! Ready to help."],
    "hello": ["Hello!", "Hi there!"],
    "who made you": ["You did, by asking me to be helpful. :)"],
    "thank you": ["You're welcome!", "Anytime!"]
}

# --------- TTS -------------
def speak(text):
    print("Assistant:", text)
    try:
        engine = pyttsx3.init()
        engine.setProperty("rate", 160)
        voices = engine.getProperty("voices")
        if len(voices) > 1:
            engine.setProperty("voice", voices[1].id)
        engine.say(text)
        engine.runAndWait()
        engine.stop()
        del engine
    except Exception as e:
        print("TTS error:", e)

# --------- Reminders ----------
def load_reminders():
    if os.path.exists(REMINDERS_FILE):
        try:
            with open(REMINDERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_reminders(reminders):
    try:
        with open(REMINDERS_FILE, "w", encoding="utf-8") as f:
            json.dump(reminders, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Reminder save error:", e)

# --------- Speech Recognition -------------
recognizer = sr.Recognizer()

def listen_for_speech(timeout=None, phrase_time_limit=8):
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=1)
        print("Listening...")
        try:
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
        except sr.WaitTimeoutError:
            print("Timeout waiting for phrase")
            return ""
        except Exception as e:
            print("Error during listen:", e)
            return ""
    try:
        text = recognizer.recognize_google(audio, language="en-IN")
        print("Heard:", text)
        return text.lower()
    except sr.UnknownValueError:
        print("Could not understand audio")
        return ""
    except sr.RequestError as e:
        print("Speech API/network error:", e)
        speak("Network error for speech recognition.")
        return ""
    except Exception as e:
        print("Recognition error:", e)
        return ""

# --------- Core Actions -----------
def tell_time():
    now = datetime.datetime.now().strftime("%I:%M %p")
    speak(f"The time is {now}")

def tell_date():
    today = datetime.datetime.now().strftime("%A, %d %B %Y")
    speak(f"Today is {today}")

def get_weather(city=None):
    if not city:
        speak("Which city?")
        city = listen_for_speech(timeout=5)
        if not city:
            speak("Sorry, I didn't catch the city name.")
            return
    try:
        url = f"https://wttr.in/{city}?format=%C+%t"
        res = requests.get(url, timeout=8)
        if res.status_code == 200:
            speak(f"The weather in {city} is {res.text.strip()}")
        else:
            speak(f"Sorry, I couldn't fetch the weather for {city}.")
    except Exception as e:
        print("Weather error:", e)
        speak("Sorry, I couldn't fetch the weather.")

def open_website(phrase):
    phrase = phrase.lower()
    if "google" in phrase:
        webbrowser.open("https://www.google.com")
        speak("Opening Google")
    elif "youtube" in phrase:
        webbrowser.open("https://www.youtube.com")
        speak("Opening YouTube")
    else:
        webbrowser.open("https://www.google.com/search?q=" + phrase.replace(" ", "+"))
        speak(f"Searching the web for {phrase}")

def open_app(name):
    path = APP_PATHS.get(name.lower())
    real_path = os.path.expandvars(path) if path else ""
    if path and os.path.exists(real_path):
        try:
            os.startfile(real_path)
            speak(f"Opening {name}")
        except Exception as e:
            print("Open app error:", e)
            speak(f"Failed to open {name}")
    else:
        speak(f"I don't have the path for {name}. You can add it in the APP_PATHS.")

def wiki_search(query):
    try:
        topic = query.replace("who is", "").replace("what is", "").strip()
        if not topic:
            speak("What would you like me to search on Wikipedia?")
            return
        speak(f"Searching Wikipedia for {topic}")
        summary = wikipedia.summary(topic, sentences=2)
        speak(summary)
    except Exception as e:
        print("Wiki error:", e)
        speak("Sorry, I couldn't get a Wikipedia summary.")

def calculate(expr):
    try:
        allowed = "0123456789+-*/(). "
        if any(ch not in allowed for ch in expr):
            speak("Sorry, I can't calculate that expression.")
            return
        result = eval(expr)
        speak(f"The result is {result}")
    except Exception as e:
        print("Calc error:", e)
        speak("Sorry, I couldn't calculate that.")

def play_music():
    folder = os.path.expandvars(MUSIC_FOLDER)
    if not os.path.isdir(folder):
        speak("Music folder not found. Please update MUSIC_FOLDER in the config.")
        return
    files = [f for f in os.listdir(folder) if f.lower().endswith((".mp3", ".wav", ".m4a"))]
    if not files:
        speak("No music files found in the folder.")
        return
    song = choice(files)
    path = os.path.join(folder, song)
    speak(f"Playing {song}")
    try:
        os.startfile(path)
    except Exception as e:
        print("Play music error:", e)
        speak("Could not play the song.")

def alarm_thread(delay_seconds, message):
    time.sleep(delay_seconds)
    speak(f"Alarm: {message}")

def set_alarm(time_str, message="Alarm"):
    try:
        now = datetime.datetime.now()
        if time_str.startswith("in "):
            parts = time_str.split()
            if "minute" in time_str:
                minutes = int(parts[1])
                delay = minutes * 60
            elif "hour" in time_str:
                hours = int(parts[1])
                delay = hours * 3600
            else:
                delay = int(parts[1])
        else:
            try:
                target = datetime.datetime.strptime(time_str, "%H:%M")
                target = target.replace(year=now.year, month=now.month, day=now.day)
                if target < now:
                    target += datetime.timedelta(days=1)
                delay = (target - now).total_seconds()
            except Exception:
                speak("Sorry, please use 'HH:MM' format or say 'in X minutes'.")
                return
        threading.Thread(target=alarm_thread, args=(delay, message), daemon=True).start()
        speak(f"Alarm set for {time_str}")
    except Exception as e:
        print("Set alarm error:", e)
        speak("Sorry, I couldn't set that alarm. Try 'set alarm for 07:30' or 'set alarm in 10 minutes'")

def add_reminder(time_str, note):
    reminders = load_reminders()
    reminders.append({"time": time_str, "note": note})
    save_reminders(reminders)
    speak("Reminder saved.")

def list_reminders():
    reminders = load_reminders()
    if not reminders:
        speak("You have no reminders.")
        return
    speak("Your reminders are:")
    for r in reminders:
        speak(f"At {r['time']}: {r['note']}")

def small_talk(cmd):
    for k, v in SMALL_TALKS.items():
        if k in cmd:
            speak(choice(v))
            return True
    return False

# --------- Command Handler ----------
def handle_command(cmd):
    cmd = cmd.lower().strip()
    if not cmd:
        return
    if small_talk(cmd):
        return
    if "time" in cmd:
        tell_time()
        return
    if "date" in cmd:
        tell_date()
        return
    if "weather" in cmd:
        if "in " in cmd:
            city = cmd.split("in ", 1)[1]
            get_weather(city)
        else:
            get_weather()
        return
    if "open" in cmd and ("website" in cmd or "youtube" in cmd or "google" in cmd):
        open_website(cmd)
        return
    if "open" in cmd:
        words = cmd.replace("open", "").strip()
        open_app(words)
        return
    if cmd.startswith("who is") or cmd.startswith("what is"):
        wiki_search(cmd)
        return
    if "play music" in cmd or cmd == "play music":
        play_music()
        return
    if cmd.startswith("play "):
        target = cmd.replace("play ", "")
        open_website(f"https://www.youtube.com/results?search_query={target}")
        speak(f"Playing {target} on YouTube")
        return
    if cmd.startswith("calculate"):
        expr = cmd.replace("calculate", "").strip()
        calculate(expr)
        return
    if "set alarm" in cmd or "alarm" in cmd:
        spoken = cmd.replace("set alarm", "").replace("for", "").strip()
        if not spoken:
            speak("What time should I set the alarm for?")
            spoken = listen_for_speech()
        set_alarm(spoken, "Alarm")
        return
    if "remind me" in cmd:
        rest = cmd.split("remind me", 1)[1].strip()
        if " at " in rest:
            note, at = rest.split(" at ", 1)
            add_reminder(at.strip(), note.replace("to", "").strip())
        else:
            speak("When should I remind you?")
            at = listen_for_speech()
            add_reminder(at, rest.replace("to", "").strip())
        return
    if "list reminders" in cmd or "show reminders" in cmd:
        list_reminders()
        return
    if "stop" in cmd or "exit" in cmd or "goodbye" in cmd or "shutdown assistant" in cmd:
        speak("Goodbye! Shutting down assistant.")
        sys.exit()
    speak(f"I did not understand fully. Searching the web for: {cmd}")
    webbrowser.open("https://www.google.com/search?q=" + cmd.replace(" ", "+"))

def main_loop():
    speak("Assistant started. Say 'Hey Assistant' to wake me up.")
    while True:
        try:
            text = listen_for_speech(timeout=5, phrase_time_limit=4)
            print(f"Wake word heard: {text}")
            if not text:
                continue
            if any(w in text for w in WAKE_WORDS):
                speak("Yes?")
                command = listen_for_speech(timeout=6, phrase_time_limit=10)
                print(f"Command heard: {command}")
                if command:
                    handle_command(command)
                else:
                    speak("I didn't hear a command.")
        except KeyboardInterrupt:
            speak("Assistant terminated by user.")
            break
        except Exception as e:
            print("Main loop error:", e)
            time.sleep(0.5)

if __name__ == "__main__":
    speak("Booting up your assistant.")
    main_loop()
