"""
Tier 1: Hand-curated English → ASL gloss pattern table.

Patterns use {SLOT} notation for variable parts:
  "I gave {PERSON} the {OBJECT}" → "{OBJECT} I GIVE-{PERSON}"

ASL grammar principles applied:
  - Topic-comment: object/topic first, then action/comment
  - Time signs at sentence start
  - WH-questions: WH-word at sentence end
  - Negation: NOT at end of clause
  - Spatial verbs use directional notation (GIVE-YOU, GIVE-ME)

Each pattern also carries `augmented` examples — slot-filled sentences used to
build the Tier 2 FAISS index corpus. These should be representative, common phrases.

Categories: greetings, farewells, responses, questions, requests, feelings,
            identity, time, location, health, food, technology, actions,
            family, weather, shopping, opinion, work, transport
"""

from typing import TypedDict


class Pattern(TypedDict):
    english: str          # pattern with {SLOT} placeholders (lowercase normalized)
    asl: str              # ASL gloss template with {SLOT} placeholders
    category: str
    augmented: list[str]  # example sentences (slots filled) for FAISS corpus


PATTERNS: list[Pattern] = [

    # ── GREETINGS ─────────────────────────────────────────────────────────────

    {"english": "hello",
     "asl": "HELLO",
     "category": "greeting",
     "augmented": ["hello", "hi there"]},

    {"english": "hi",
     "asl": "HELLO",
     "category": "greeting",
     "augmented": ["hi", "hey"]},

    {"english": "good morning",
     "asl": "GOOD MORNING",
     "category": "greeting",
     "augmented": ["good morning", "morning"]},

    {"english": "good afternoon",
     "asl": "GOOD AFTERNOON",
     "category": "greeting",
     "augmented": ["good afternoon"]},

    {"english": "good evening",
     "asl": "GOOD EVENING",
     "category": "greeting",
     "augmented": ["good evening"]},

    {"english": "good night",
     "asl": "GOOD NIGHT",
     "category": "greeting",
     "augmented": ["good night", "night"]},

    {"english": "how are you",
     "asl": "YOU HOW YOU",
     "category": "greeting",
     "augmented": ["how are you", "how are you doing"]},

    {"english": "how are you doing",
     "asl": "YOU HOW YOU",
     "category": "greeting",
     "augmented": ["how are you doing", "how are you today"]},

    {"english": "nice to meet you",
     "asl": "MEET YOU NICE",
     "category": "greeting",
     "augmented": ["nice to meet you", "pleased to meet you"]},

    {"english": "pleased to meet you",
     "asl": "MEET YOU NICE",
     "category": "greeting",
     "augmented": ["pleased to meet you"]},

    {"english": "welcome",
     "asl": "WELCOME",
     "category": "greeting",
     "augmented": ["welcome", "you are welcome here"]},

    {"english": "long time no see",
     "asl": "LONG-TIME NO SEE",
     "category": "greeting",
     "augmented": ["long time no see", "haven't seen you in a long time"]},

    {"english": "it's good to see you",
     "asl": "SEE YOU GOOD",
     "category": "greeting",
     "augmented": ["it's good to see you", "great to see you"]},

    # ── FAREWELLS ─────────────────────────────────────────────────────────────

    {"english": "goodbye",
     "asl": "GOODBYE",
     "category": "farewell",
     "augmented": ["goodbye", "bye", "bye bye"]},

    {"english": "bye",
     "asl": "GOODBYE",
     "category": "farewell",
     "augmented": ["bye", "bye now"]},

    {"english": "see you later",
     "asl": "LATER SEE-YOU",
     "category": "farewell",
     "augmented": ["see you later", "catch you later"]},

    {"english": "see you tomorrow",
     "asl": "TOMORROW SEE-YOU",
     "category": "farewell",
     "augmented": ["see you tomorrow", "until tomorrow"]},

    {"english": "see you soon",
     "asl": "SOON SEE-YOU",
     "category": "farewell",
     "augmented": ["see you soon", "talk to you soon"]},

    {"english": "take care",
     "asl": "TAKE-CARE",
     "category": "farewell",
     "augmented": ["take care", "take care of yourself"]},

    {"english": "have a good day",
     "asl": "YOUR DAY GOOD",
     "category": "farewell",
     "augmented": ["have a good day", "have a great day"]},

    {"english": "have a good night",
     "asl": "YOUR NIGHT GOOD",
     "category": "farewell",
     "augmented": ["have a good night", "have a nice night"]},

    # ── COMMON RESPONSES ──────────────────────────────────────────────────────

    {"english": "thank you",
     "asl": "THANK-YOU",
     "category": "response",
     "augmented": ["thank you", "thanks"]},

    {"english": "thanks",
     "asl": "THANK-YOU",
     "category": "response",
     "augmented": ["thanks", "thank you very much"]},

    {"english": "you're welcome",
     "asl": "WELCOME",
     "category": "response",
     "augmented": ["you're welcome", "no problem", "of course"]},

    {"english": "no problem",
     "asl": "NO PROBLEM",
     "category": "response",
     "augmented": ["no problem", "it's no problem"]},

    {"english": "i'm sorry",
     "asl": "SORRY I",
     "category": "response",
     "augmented": ["i'm sorry", "i am sorry", "sorry"]},

    {"english": "excuse me",
     "asl": "EXCUSE-ME",
     "category": "response",
     "augmented": ["excuse me", "pardon me"]},

    {"english": "yes",
     "asl": "YES",
     "category": "response",
     "augmented": ["yes", "yeah", "yep"]},

    {"english": "no",
     "asl": "NO",
     "category": "response",
     "augmented": ["no", "nope", "no thank you"]},

    {"english": "maybe",
     "asl": "MAYBE",
     "category": "response",
     "augmented": ["maybe", "perhaps", "possibly"]},

    {"english": "okay",
     "asl": "OKAY",
     "category": "response",
     "augmented": ["okay", "ok", "alright"]},

    {"english": "i understand",
     "asl": "UNDERSTAND I",
     "category": "response",
     "augmented": ["i understand", "i get it", "i see"]},

    {"english": "i see",
     "asl": "I-SEE",
     "category": "response",
     "augmented": ["i see", "i understand now"]},

    {"english": "i don't understand",
     "asl": "UNDERSTAND I NOT",
     "category": "response",
     "augmented": ["i don't understand", "i do not understand", "i'm confused"]},

    {"english": "please repeat that",
     "asl": "REPEAT PLEASE",
     "category": "response",
     "augmented": ["please repeat that", "say that again", "can you repeat that"]},

    {"english": "please slow down",
     "asl": "SLOW-DOWN PLEASE",
     "category": "response",
     "augmented": ["please slow down", "speak more slowly please"]},

    {"english": "that's right",
     "asl": "RIGHT THAT",
     "category": "response",
     "augmented": ["that's right", "that is correct", "exactly right"]},

    {"english": "that's wrong",
     "asl": "WRONG THAT",
     "category": "response",
     "augmented": ["that's wrong", "that is not correct", "incorrect"]},

    {"english": "of course",
     "asl": "OF-COURSE",
     "category": "response",
     "augmented": ["of course", "absolutely", "certainly"]},

    # ── QUESTIONS — BASIC ─────────────────────────────────────────────────────

    {"english": "what is your {NOUN}",
     "asl": "YOUR {NOUN} WHAT",
     "category": "question",
     "augmented": ["what is your name", "what is your address", "what is your phone number"]},

    {"english": "what is your name",
     "asl": "YOUR NAME WHAT",
     "category": "question",
     "augmented": ["what is your name", "what's your name"]},

    {"english": "where is the {PLACE}",
     "asl": "{PLACE} WHERE",
     "category": "question",
     "augmented": ["where is the bathroom", "where is the exit", "where is the hospital"]},

    {"english": "where is {THING}",
     "asl": "{THING} WHERE",
     "category": "question",
     "augmented": ["where is my bag", "where is the key", "where is my phone"]},

    {"english": "when is {EVENT}",
     "asl": "{EVENT} WHEN",
     "category": "question",
     "augmented": ["when is the meeting", "when is the appointment", "when is dinner"]},

    {"english": "who is {PERSON}",
     "asl": "{PERSON} WHO",
     "category": "question",
     "augmented": ["who is that person", "who is calling", "who is at the door"]},

    {"english": "why are you {VERB}ing",
     "asl": "YOU {VERB} WHY",
     "category": "question",
     "augmented": ["why are you leaving", "why are you waiting", "why are you crying"]},

    {"english": "how much does {THING} cost",
     "asl": "{THING} COST HOW-MUCH",
     "category": "question",
     "augmented": ["how much does this cost", "how much does the ticket cost", "how much does food cost"]},

    {"english": "how many {THING} do you have",
     "asl": "YOU HAVE {THING} HOW-MANY",
     "category": "question",
     "augmented": ["how many people do you have", "how many tickets do you have", "how many kids do you have"]},

    {"english": "what time is it",
     "asl": "TIME WHAT",
     "category": "question",
     "augmented": ["what time is it", "what is the time"]},

    {"english": "what day is it today",
     "asl": "TODAY DAY WHAT",
     "category": "question",
     "augmented": ["what day is it today", "what day is today"]},

    {"english": "what are you doing",
     "asl": "YOU DO WHAT",
     "category": "question",
     "augmented": ["what are you doing", "what are you doing now"]},

    {"english": "what do you want",
     "asl": "YOU WANT WHAT",
     "category": "question",
     "augmented": ["what do you want", "what would you like"]},

    {"english": "what happened",
     "asl": "HAPPEN WHAT",
     "category": "question",
     "augmented": ["what happened", "what's going on", "what's wrong"]},

    {"english": "do you understand",
     "asl": "YOU UNDERSTAND",
     "category": "question",
     "augmented": ["do you understand", "do you understand me"]},

    {"english": "do you {VERB}",
     "asl": "YOU {VERB}",
     "category": "question",
     "augmented": ["do you know", "do you agree", "do you remember"]},

    {"english": "do you want {THING}",
     "asl": "{THING} YOU WANT",
     "category": "question",
     "augmented": ["do you want coffee", "do you want help", "do you want more"]},

    {"english": "can you {VERB}",
     "asl": "YOU {VERB} CAN",
     "category": "question",
     "augmented": ["can you help", "can you wait", "can you come here"]},

    {"english": "can you help me",
     "asl": "YOU HELP ME CAN",
     "category": "question",
     "augmented": ["can you help me", "could you help me"]},

    {"english": "how old are you",
     "asl": "YOUR AGE WHAT",
     "category": "question",
     "augmented": ["how old are you", "what is your age"]},

    {"english": "where are you from",
     "asl": "YOU FROM WHERE",
     "category": "question",
     "augmented": ["where are you from", "what country are you from"]},

    {"english": "what do you do",
     "asl": "YOUR WORK WHAT",
     "category": "question",
     "augmented": ["what do you do", "what is your job", "what do you do for work"]},

    # ── NEEDS AND REQUESTS ────────────────────────────────────────────────────

    {"english": "i want {THING}",
     "asl": "{THING} I WANT",
     "category": "request",
     "augmented": ["i want water", "i want coffee", "i want help", "i want more time"]},

    {"english": "i need {THING}",
     "asl": "{THING} I NEED",
     "category": "request",
     "augmented": ["i need help", "i need water", "i need a doctor", "i need more time"]},

    {"english": "i need help",
     "asl": "HELP I NEED",
     "category": "request",
     "augmented": ["i need help", "i need assistance"]},

    {"english": "i would like {THING}",
     "asl": "{THING} I WANT",
     "category": "request",
     "augmented": ["i would like water", "i would like coffee", "i would like a table"]},

    {"english": "can i have {THING}",
     "asl": "{THING} I CAN HAVE",
     "category": "request",
     "augmented": ["can i have water", "can i have the menu", "can i have a receipt"]},

    {"english": "may i have {THING}",
     "asl": "{THING} I CAN HAVE",
     "category": "request",
     "augmented": ["may i have the check", "may i have a receipt", "may i have water"]},

    {"english": "please give me {THING}",
     "asl": "PLEASE {THING} GIVE-ME",
     "category": "request",
     "augmented": ["please give me water", "please give me the paper", "please give me time"]},

    {"english": "please {VERB}",
     "asl": "PLEASE {VERB}",
     "category": "request",
     "augmented": ["please wait", "please help", "please stop", "please come back"]},

    {"english": "wait a moment",
     "asl": "WAIT MOMENT",
     "category": "request",
     "augmented": ["wait a moment", "just a moment", "one second"]},

    {"english": "i'll be right back",
     "asl": "RIGHT-BACK I",
     "category": "request",
     "augmented": ["i'll be right back", "be right back", "brb"]},

    {"english": "can you write it down",
     "asl": "WRITE-DOWN YOU CAN",
     "category": "request",
     "augmented": ["can you write it down", "please write that down"]},

    {"english": "show me",
     "asl": "SHOW ME",
     "category": "request",
     "augmented": ["show me", "show me how", "can you show me"]},

    {"english": "tell me more",
     "asl": "MORE TELL-ME",
     "category": "request",
     "augmented": ["tell me more", "tell me about it", "tell me more about that"]},

    {"english": "stop",
     "asl": "STOP",
     "category": "request",
     "augmented": ["stop", "please stop", "stop it"]},

    {"english": "help",
     "asl": "HELP",
     "category": "request",
     "augmented": ["help", "help me", "i need help"]},

    # ── FEELINGS AND STATE ────────────────────────────────────────────────────

    {"english": "i am {ADJECTIVE}",
     "asl": "{ADJECTIVE} I",
     "category": "feeling",
     "augmented": ["i am happy", "i am tired", "i am fine", "i am ready", "i am busy"]},

    {"english": "i feel {ADJECTIVE}",
     "asl": "{ADJECTIVE} I FEEL",
     "category": "feeling",
     "augmented": ["i feel happy", "i feel sad", "i feel sick", "i feel better"]},

    {"english": "i am happy",
     "asl": "HAPPY I",
     "category": "feeling",
     "augmented": ["i am happy", "i'm happy", "i feel happy"]},

    {"english": "i am sad",
     "asl": "SAD I",
     "category": "feeling",
     "augmented": ["i am sad", "i'm sad", "i feel sad"]},

    {"english": "i am tired",
     "asl": "TIRED I",
     "category": "feeling",
     "augmented": ["i am tired", "i'm tired", "i feel tired"]},

    {"english": "i am hungry",
     "asl": "HUNGRY I",
     "category": "feeling",
     "augmented": ["i am hungry", "i'm hungry", "i'm really hungry"]},

    {"english": "i am thirsty",
     "asl": "THIRSTY I",
     "category": "feeling",
     "augmented": ["i am thirsty", "i'm thirsty", "i need water i'm thirsty"]},

    {"english": "i am sick",
     "asl": "SICK I",
     "category": "feeling",
     "augmented": ["i am sick", "i'm sick", "i don't feel well"]},

    {"english": "i am fine",
     "asl": "FINE I",
     "category": "feeling",
     "augmented": ["i am fine", "i'm fine", "i'm okay"]},

    {"english": "i am not {ADJECTIVE}",
     "asl": "{ADJECTIVE} I NOT",
     "category": "feeling",
     "augmented": ["i am not tired", "i am not hungry", "i am not ready"]},

    {"english": "are you okay",
     "asl": "YOU OKAY",
     "category": "feeling",
     "augmented": ["are you okay", "are you alright", "you okay"]},

    {"english": "are you hungry",
     "asl": "HUNGRY YOU",
     "category": "feeling",
     "augmented": ["are you hungry", "are you thirsty"]},

    {"english": "he is {ADJECTIVE}",
     "asl": "{ADJECTIVE} HE",
     "category": "feeling",
     "augmented": ["he is happy", "he is tired", "he is sick"]},

    {"english": "she is {ADJECTIVE}",
     "asl": "{ADJECTIVE} SHE",
     "category": "feeling",
     "augmented": ["she is happy", "she is tired", "she is busy"]},

    {"english": "they are {ADJECTIVE}",
     "asl": "{ADJECTIVE} THEY",
     "category": "feeling",
     "augmented": ["they are ready", "they are tired", "they are happy"]},

    # ── IDENTITY / INTRODUCTION ───────────────────────────────────────────────

    {"english": "my name is {NAME}",
     "asl": "MY NAME {NAME}",
     "category": "identity",
     "augmented": ["my name is john", "my name is sarah", "my name is alex"]},

    {"english": "i am {AGE} years old",
     "asl": "MY AGE {AGE}",
     "category": "identity",
     "augmented": ["i am 30 years old", "i am 25 years old", "i am 45 years old"]},

    {"english": "i am from {PLACE}",
     "asl": "FROM {PLACE} I",
     "category": "identity",
     "augmented": ["i am from new york", "i am from california", "i am from texas"]},

    {"english": "i work as a {JOB}",
     "asl": "MY WORK {JOB}",
     "category": "identity",
     "augmented": ["i work as a teacher", "i work as a doctor", "i work as an engineer"]},

    {"english": "i work at {PLACE}",
     "asl": "AT {PLACE} I WORK",
     "category": "identity",
     "augmented": ["i work at the hospital", "i work at the school", "i work at home"]},

    {"english": "i live in {PLACE}",
     "asl": "I LIVE {PLACE}",
     "category": "identity",
     "augmented": ["i live in new york", "i live in chicago", "i live in los angeles"]},

    {"english": "i am married",
     "asl": "MARRIED I",
     "category": "identity",
     "augmented": ["i am married", "i'm married"]},

    {"english": "i am not married",
     "asl": "MARRIED I NOT",
     "category": "identity",
     "augmented": ["i am not married", "i'm single"]},

    {"english": "i am deaf",
     "asl": "DEAF I",
     "category": "identity",
     "augmented": ["i am deaf", "i'm deaf"]},

    {"english": "i use sign language",
     "asl": "SIGN-LANGUAGE I USE",
     "category": "identity",
     "augmented": ["i use sign language", "i communicate in sign language"]},

    {"english": "do you know sign language",
     "asl": "SIGN-LANGUAGE YOU KNOW",
     "category": "identity",
     "augmented": ["do you know sign language", "can you sign", "do you sign"]},

    {"english": "please speak slowly",
     "asl": "SLOW SPEAK PLEASE",
     "category": "identity",
     "augmented": ["please speak slowly", "speak slowly please", "talk slowly please"]},

    # ── TIME EXPRESSIONS ──────────────────────────────────────────────────────

    {"english": "what time does {EVENT} start",
     "asl": "{EVENT} START WHEN",
     "category": "time",
     "augmented": ["what time does the meeting start", "what time does the movie start",
                   "what time does the store open"]},

    {"english": "i will {VERB} later",
     "asl": "LATER I WILL {VERB}",
     "category": "time",
     "augmented": ["i will call later", "i will come back later", "i will finish later"]},

    {"english": "i will {VERB} tomorrow",
     "asl": "TOMORROW I WILL {VERB}",
     "category": "time",
     "augmented": ["i will call tomorrow", "i will come tomorrow", "i will finish tomorrow"]},

    {"english": "i {VERB}ed yesterday",
     "asl": "YESTERDAY I {VERB}",
     "category": "time",
     "augmented": ["i worked yesterday", "i called yesterday", "i went yesterday"]},

    {"english": "see you next week",
     "asl": "NEXT-WEEK SEE-YOU",
     "category": "time",
     "augmented": ["see you next week", "catch you next week"]},

    {"english": "it will take {DURATION}",
     "asl": "{DURATION} TAKE-TIME",
     "category": "time",
     "augmented": ["it will take five minutes", "it will take an hour", "it will take two days"]},

    {"english": "i'll do it now",
     "asl": "NOW I DO",
     "category": "time",
     "augmented": ["i'll do it now", "doing it now", "i'll take care of it now"]},

    {"english": "i did it already",
     "asl": "ALREADY I DO",
     "category": "time",
     "augmented": ["i did it already", "i already did it", "already done"]},

    {"english": "not yet",
     "asl": "NOT-YET",
     "category": "time",
     "augmented": ["not yet", "i haven't done it yet", "not finished yet"]},

    {"english": "in a few minutes",
     "asl": "FEW-MINUTES",
     "category": "time",
     "augmented": ["in a few minutes", "a few minutes", "just a few minutes"]},

    {"english": "i have been waiting for {DURATION}",
     "asl": "{DURATION} I WAIT",
     "category": "time",
     "augmented": ["i have been waiting for an hour", "i have been waiting for twenty minutes",
                   "i have been waiting for a long time"]},

    {"english": "it is {TIME} o'clock",
     "asl": "TIME {TIME}",
     "category": "time",
     "augmented": ["it is three o'clock", "it is noon o'clock", "it is five o'clock"]},

    # ── LOCATION AND DIRECTIONS ───────────────────────────────────────────────

    {"english": "where is the bathroom",
     "asl": "BATHROOM WHERE",
     "category": "location",
     "augmented": ["where is the bathroom", "where is the restroom", "where is the toilet"]},

    {"english": "where is the exit",
     "asl": "EXIT WHERE",
     "category": "location",
     "augmented": ["where is the exit", "where is the way out"]},

    {"english": "turn left",
     "asl": "TURN-LEFT",
     "category": "location",
     "augmented": ["turn left", "go left", "left turn"]},

    {"english": "turn right",
     "asl": "TURN-RIGHT",
     "category": "location",
     "augmented": ["turn right", "go right", "right turn"]},

    {"english": "go straight",
     "asl": "GO-STRAIGHT",
     "category": "location",
     "augmented": ["go straight", "straight ahead", "keep going straight"]},

    {"english": "it is near {PLACE}",
     "asl": "{PLACE} NEAR",
     "category": "location",
     "augmented": ["it is near the station", "it is near the hospital", "it is near the store"]},

    {"english": "it is far from {PLACE}",
     "asl": "{PLACE} FAR",
     "category": "location",
     "augmented": ["it is far from the center", "it is far from here", "it is far from downtown"]},

    {"english": "i am at {PLACE}",
     "asl": "AT {PLACE} I",
     "category": "location",
     "augmented": ["i am at home", "i am at the store", "i am at the hospital"]},

    {"english": "i am going to {PLACE}",
     "asl": "{PLACE} GO I",
     "category": "location",
     "augmented": ["i am going to the store", "i am going to work", "i am going to the hospital"]},

    {"english": "how far is {PLACE}",
     "asl": "{PLACE} FAR HOW",
     "category": "location",
     "augmented": ["how far is the hospital", "how far is the station", "how far is the airport"]},

    {"english": "i am lost",
     "asl": "LOST I",
     "category": "location",
     "augmented": ["i am lost", "i'm lost", "i got lost"]},

    {"english": "can you show me the way to {PLACE}",
     "asl": "{PLACE} WAY SHOW-ME YOU CAN",
     "category": "location",
     "augmented": ["can you show me the way to the station", "can you show me the way to downtown"]},

    # ── HEALTH AND EMERGENCY ──────────────────────────────────────────────────

    {"english": "i need a doctor",
     "asl": "DOCTOR I NEED",
     "category": "health",
     "augmented": ["i need a doctor", "i need to see a doctor", "call a doctor"]},

    {"english": "call an ambulance",
     "asl": "AMBULANCE CALL",
     "category": "health",
     "augmented": ["call an ambulance", "please call an ambulance", "we need an ambulance"]},

    {"english": "i am in pain",
     "asl": "PAIN I",
     "category": "health",
     "augmented": ["i am in pain", "i'm in pain", "i have pain"]},

    {"english": "this hurts",
     "asl": "HURT THIS",
     "category": "health",
     "augmented": ["this hurts", "it hurts here", "that hurts"]},

    {"english": "i am allergic to {THING}",
     "asl": "{THING} ALLERGIC I",
     "category": "health",
     "augmented": ["i am allergic to peanuts", "i am allergic to penicillin",
                   "i am allergic to shellfish"]},

    {"english": "where is the hospital",
     "asl": "HOSPITAL WHERE",
     "category": "health",
     "augmented": ["where is the hospital", "where is the nearest hospital",
                   "take me to the hospital"]},

    {"english": "i don't feel well",
     "asl": "FEEL-WELL I NOT",
     "category": "health",
     "augmented": ["i don't feel well", "i'm not feeling well", "i feel unwell"]},

    {"english": "i have {CONDITION}",
     "asl": "{CONDITION} I HAVE",
     "category": "health",
     "augmented": ["i have diabetes", "i have a headache", "i have a fever"]},

    {"english": "i take medication for {CONDITION}",
     "asl": "{CONDITION} MEDICINE I TAKE",
     "category": "health",
     "augmented": ["i take medication for diabetes", "i take medication for high blood pressure",
                   "i take medication for anxiety"]},

    {"english": "emergency",
     "asl": "EMERGENCY",
     "category": "health",
     "augmented": ["emergency", "this is an emergency", "call 911"]},

    {"english": "call the police",
     "asl": "POLICE CALL",
     "category": "health",
     "augmented": ["call the police", "please call the police", "we need the police"]},

    {"english": "i need my medicine",
     "asl": "MY MEDICINE I NEED",
     "category": "health",
     "augmented": ["i need my medicine", "i need my medication", "where is my medicine"]},

    # ── FOOD AND EATING ───────────────────────────────────────────────────────

    {"english": "what do you want to eat",
     "asl": "EAT YOU WANT WHAT",
     "category": "food",
     "augmented": ["what do you want to eat", "what would you like to eat", "what should we eat"]},

    {"english": "the food is {ADJECTIVE}",
     "asl": "FOOD {ADJECTIVE}",
     "category": "food",
     "augmented": ["the food is delicious", "the food is good", "the food is hot"]},

    {"english": "i like {FOOD}",
     "asl": "{FOOD} I LIKE",
     "category": "food",
     "augmented": ["i like pizza", "i like coffee", "i like sushi"]},

    {"english": "i don't like {FOOD}",
     "asl": "{FOOD} I LIKE NOT",
     "category": "food",
     "augmented": ["i don't like spicy food", "i don't like fish", "i don't like coffee"]},

    {"english": "can i order {FOOD}",
     "asl": "{FOOD} I ORDER CAN",
     "category": "food",
     "augmented": ["can i order the pasta", "can i order coffee", "can i order more"]},

    {"english": "the bill please",
     "asl": "BILL PLEASE",
     "category": "food",
     "augmented": ["the bill please", "check please", "can i have the check"]},

    {"english": "i am vegetarian",
     "asl": "VEGETARIAN I",
     "category": "food",
     "augmented": ["i am vegetarian", "i'm vegetarian", "i don't eat meat"]},

    {"english": "do you have {FOOD}",
     "asl": "{FOOD} YOU HAVE",
     "category": "food",
     "augmented": ["do you have coffee", "do you have vegetarian options", "do you have water"]},

    {"english": "that was delicious",
     "asl": "DELICIOUS THAT",
     "category": "food",
     "augmented": ["that was delicious", "the food was delicious", "that tasted great"]},

    {"english": "i want water",
     "asl": "WATER I WANT",
     "category": "food",
     "augmented": ["i want water", "can i have water", "i need water"]},

    # ── TECHNOLOGY AND COMMUNICATION ──────────────────────────────────────────

    {"english": "my phone number is {NUMBER}",
     "asl": "MY PHONE-NUMBER {NUMBER}",
     "category": "technology",
     "augmented": ["my phone number is five five five one two three four",
                   "my phone number is eight hundred five five five"]},

    {"english": "can you text me",
     "asl": "TEXT ME YOU CAN",
     "category": "technology",
     "augmented": ["can you text me", "please text me", "text me later"]},

    {"english": "i will call you",
     "asl": "CALL YOU I WILL",
     "category": "technology",
     "augmented": ["i will call you", "i'll call you", "i'll call you later"]},

    {"english": "what is your email",
     "asl": "YOUR EMAIL WHAT",
     "category": "technology",
     "augmented": ["what is your email", "what's your email address"]},

    {"english": "send me the {THING}",
     "asl": "{THING} SEND-ME",
     "category": "technology",
     "augmented": ["send me the file", "send me the photo", "send me the address"]},

    {"english": "can you type it",
     "asl": "TYPE IT YOU CAN",
     "category": "technology",
     "augmented": ["can you type it", "please type what you're saying", "can you write it"]},

    {"english": "the internet is not working",
     "asl": "INTERNET NOT WORK",
     "category": "technology",
     "augmented": ["the internet is not working", "the wifi is down", "no internet connection"]},

    # ── COMMON ACTIONS ────────────────────────────────────────────────────────

    {"english": "i gave you the {OBJECT}",
     "asl": "{OBJECT} I GIVE-YOU",
     "category": "action",
     "augmented": ["i gave you the book", "i gave you the key", "i gave you the money"]},

    {"english": "i gave {PERSON} the {OBJECT}",
     "asl": "{OBJECT} I GIVE-{PERSON}",
     "category": "action",
     "augmented": ["i gave john the book", "i gave her the key", "i gave him the money"]},

    {"english": "can you give me {THING}",
     "asl": "{THING} GIVE-ME YOU CAN",
     "category": "action",
     "augmented": ["can you give me water", "can you give me the paper", "can you give me a hand"]},

    {"english": "i will meet you at {PLACE}",
     "asl": "{PLACE} MEET YOU I WILL",
     "category": "action",
     "augmented": ["i will meet you at the station", "i will meet you at the coffee shop",
                   "i will meet you at home"]},

    {"english": "i am waiting for you",
     "asl": "YOU WAIT I",
     "category": "action",
     "augmented": ["i am waiting for you", "i'm waiting for you", "been waiting for you"]},

    {"english": "i lost my {THING}",
     "asl": "MY {THING} LOSE I",
     "category": "action",
     "augmented": ["i lost my phone", "i lost my wallet", "i lost my key"]},

    {"english": "i found it",
     "asl": "FIND I",
     "category": "action",
     "augmented": ["i found it", "i found my phone", "i found the key"]},

    {"english": "i want to buy {THING}",
     "asl": "{THING} BUY I WANT",
     "category": "action",
     "augmented": ["i want to buy a ticket", "i want to buy coffee", "i want to buy this"]},

    {"english": "do you want to {VERB}",
     "asl": "YOU WANT {VERB}",
     "category": "action",
     "augmented": ["do you want to go", "do you want to eat", "do you want to come"]},

    {"english": "let's go to {PLACE}",
     "asl": "{PLACE} GO WE",
     "category": "action",
     "augmented": ["let's go to the store", "let's go to the park", "let's go to dinner"]},

    {"english": "i can {VERB}",
     "asl": "{VERB} I CAN",
     "category": "action",
     "augmented": ["i can help", "i can come", "i can drive"]},

    {"english": "i can't {VERB}",
     "asl": "{VERB} I CAN'T",
     "category": "action",
     "augmented": ["i can't come", "i can't hear you", "i can't make it"]},

    {"english": "i don't {VERB}",
     "asl": "{VERB} I NOT",
     "category": "action",
     "augmented": ["i don't know", "i don't have it", "i don't understand"]},

    {"english": "i will {VERB}",
     "asl": "WILL I {VERB}",
     "category": "action",
     "augmented": ["i will call", "i will come", "i will help"]},

    {"english": "i'm going to {VERB}",
     "asl": "FUTURE I {VERB}",
     "category": "action",
     "augmented": ["i'm going to call", "i'm going to leave", "i'm going to help"]},

    {"english": "i just {VERB}ed",
     "asl": "JUST I {VERB}",
     "category": "action",
     "augmented": ["i just arrived", "i just called", "i just finished"]},

    {"english": "i went to {PLACE}",
     "asl": "{PLACE} I GO PAST",
     "category": "action",
     "augmented": ["i went to the store", "i went to the hospital", "i went to work"]},

    {"english": "i think {CLAUSE}",
     "asl": "{CLAUSE} I THINK",
     "category": "action",
     "augmented": ["i think it's fine", "i think we should go", "i think that's right"]},

    {"english": "i know {CLAUSE}",
     "asl": "{CLAUSE} I KNOW",
     "category": "action",
     "augmented": ["i know the answer", "i know what happened", "i know that"]},

    {"english": "i don't know",
     "asl": "KNOW I NOT",
     "category": "action",
     "augmented": ["i don't know", "i'm not sure", "i have no idea"]},

    {"english": "i'm not sure",
     "asl": "SURE I NOT",
     "category": "action",
     "augmented": ["i'm not sure", "i am not sure", "not sure about that"]},

    {"english": "i agree",
     "asl": "AGREE I",
     "category": "action",
     "augmented": ["i agree", "i agree with you", "that's what i think too"]},

    {"english": "i disagree",
     "asl": "DISAGREE I",
     "category": "action",
     "augmented": ["i disagree", "i don't agree", "i disagree with that"]},

    # ── FAMILY ────────────────────────────────────────────────────────────────

    {"english": "this is my {FAMILY_MEMBER}",
     "asl": "MY {FAMILY_MEMBER} THIS",
     "category": "family",
     "augmented": ["this is my mother", "this is my brother", "this is my wife"]},

    {"english": "my {FAMILY_MEMBER} is {ADJECTIVE}",
     "asl": "MY {FAMILY_MEMBER} {ADJECTIVE}",
     "category": "family",
     "augmented": ["my mother is sick", "my son is happy", "my sister is tired"]},

    {"english": "i have a {FAMILY_MEMBER}",
     "asl": "{FAMILY_MEMBER} I HAVE",
     "category": "family",
     "augmented": ["i have a sister", "i have a brother", "i have a daughter"]},

    {"english": "my {FAMILY_MEMBER}'s name is {NAME}",
     "asl": "MY {FAMILY_MEMBER} NAME {NAME}",
     "category": "family",
     "augmented": ["my mother's name is mary", "my father's name is john",
                   "my daughter's name is emma"]},

    {"english": "where is your {FAMILY_MEMBER}",
     "asl": "YOUR {FAMILY_MEMBER} WHERE",
     "category": "family",
     "augmented": ["where is your mother", "where is your husband", "where is your child"]},

    {"english": "i miss my {FAMILY_MEMBER}",
     "asl": "MY {FAMILY_MEMBER} MISS I",
     "category": "family",
     "augmented": ["i miss my mother", "i miss my family", "i miss my daughter"]},

    {"english": "how is your {FAMILY_MEMBER}",
     "asl": "YOUR {FAMILY_MEMBER} HOW",
     "category": "family",
     "augmented": ["how is your mother", "how is your family", "how is your son"]},

    {"english": "i have {NUMBER} children",
     "asl": "I HAVE CHILDREN {NUMBER}",
     "category": "family",
     "augmented": ["i have two children", "i have three children", "i have one child"]},

    # ── WEATHER ───────────────────────────────────────────────────────────────

    {"english": "what is the weather today",
     "asl": "TODAY WEATHER WHAT",
     "category": "weather",
     "augmented": ["what is the weather today", "what's the weather like today",
                   "how is the weather"]},

    {"english": "it is {ADJECTIVE} outside",
     "asl": "OUTSIDE {ADJECTIVE}",
     "category": "weather",
     "augmented": ["it is cold outside", "it is hot outside", "it is nice outside"]},

    {"english": "it is raining",
     "asl": "RAIN",
     "category": "weather",
     "augmented": ["it is raining", "it's raining", "it's raining outside"]},

    {"english": "it is snowing",
     "asl": "SNOW",
     "category": "weather",
     "augmented": ["it is snowing", "it's snowing", "it's snowing outside"]},

    {"english": "it is hot",
     "asl": "HOT",
     "category": "weather",
     "augmented": ["it is hot", "it's hot today", "very hot today"]},

    {"english": "it is cold",
     "asl": "COLD",
     "category": "weather",
     "augmented": ["it is cold", "it's cold today", "very cold outside"]},

    {"english": "the weather is nice",
     "asl": "WEATHER NICE",
     "category": "weather",
     "augmented": ["the weather is nice", "nice weather today", "beautiful weather"]},

    {"english": "it is windy",
     "asl": "WIND",
     "category": "weather",
     "augmented": ["it is windy", "it's very windy", "windy today"]},

    # ── SHOPPING AND MONEY ────────────────────────────────────────────────────

    {"english": "how much is this",
     "asl": "THIS COST HOW-MUCH",
     "category": "shopping",
     "augmented": ["how much is this", "how much does this cost", "what is the price"]},

    {"english": "that is expensive",
     "asl": "EXPENSIVE THAT",
     "category": "shopping",
     "augmented": ["that is expensive", "that's expensive", "too expensive"]},

    {"english": "that is cheap",
     "asl": "CHEAP THAT",
     "category": "shopping",
     "augmented": ["that is cheap", "that's cheap", "very affordable"]},

    {"english": "i don't have enough money",
     "asl": "MONEY ENOUGH I NOT HAVE",
     "category": "shopping",
     "augmented": ["i don't have enough money", "i don't have the money", "i can't afford it"]},

    {"english": "can i pay with card",
     "asl": "CARD PAY I CAN",
     "category": "shopping",
     "augmented": ["can i pay with card", "do you take credit cards", "is card okay"]},

    {"english": "do you take cash",
     "asl": "CASH YOU TAKE",
     "category": "shopping",
     "augmented": ["do you take cash", "can i pay cash", "cash only"]},

    {"english": "keep the change",
     "asl": "CHANGE KEEP",
     "category": "shopping",
     "augmented": ["keep the change", "you can keep the change"]},

    {"english": "i want to return this",
     "asl": "THIS RETURN I WANT",
     "category": "shopping",
     "augmented": ["i want to return this", "i need to return this item",
                   "i'd like to return this"]},

    {"english": "do you have this in a different size",
     "asl": "DIFFERENT SIZE THIS YOU HAVE",
     "category": "shopping",
     "augmented": ["do you have this in a different size", "do you have a larger size",
                   "do you have a smaller size"]},

    # ── OPINION AND COGNITION ─────────────────────────────────────────────────

    {"english": "that's interesting",
     "asl": "INTERESTING THAT",
     "category": "opinion",
     "augmented": ["that's interesting", "very interesting", "that is interesting"]},

    {"english": "i was wrong",
     "asl": "WRONG I",
     "category": "opinion",
     "augmented": ["i was wrong", "i made a mistake", "i was incorrect"]},

    {"english": "you are right",
     "asl": "RIGHT YOU",
     "category": "opinion",
     "augmented": ["you are right", "you're right", "you were right"]},

    {"english": "i believe {CLAUSE}",
     "asl": "{CLAUSE} I THINK",
     "category": "opinion",
     "augmented": ["i believe you", "i believe that's correct", "i believe it's true"]},

    {"english": "in my opinion {CLAUSE}",
     "asl": "MY OPINION {CLAUSE}",
     "category": "opinion",
     "augmented": ["in my opinion that's wrong", "in my opinion we should go",
                   "in my opinion it's fine"]},

    {"english": "that doesn't make sense",
     "asl": "THAT MAKE-SENSE NOT",
     "category": "opinion",
     "augmented": ["that doesn't make sense", "that makes no sense", "i don't understand that"]},

    # ── WORK AND SCHOOL ───────────────────────────────────────────────────────

    {"english": "i have a meeting at {TIME}",
     "asl": "{TIME} MEETING I HAVE",
     "category": "work",
     "augmented": ["i have a meeting at three", "i have a meeting at noon",
                   "i have a meeting at two o'clock"]},

    {"english": "i am late for {EVENT}",
     "asl": "LATE {EVENT} I",
     "category": "work",
     "augmented": ["i am late for work", "i am late for the meeting", "i am late for class"]},

    {"english": "i need to finish {TASK} by {TIME}",
     "asl": "{TIME} {TASK} FINISH I NEED",
     "category": "work",
     "augmented": ["i need to finish the report by friday", "i need to finish this by tomorrow",
                   "i need to finish the project by next week"]},

    {"english": "can we reschedule the {EVENT}",
     "asl": "{EVENT} RESCHEDULE CAN WE",
     "category": "work",
     "augmented": ["can we reschedule the meeting", "can we reschedule the appointment",
                   "can we reschedule that"]},

    {"english": "i have a question",
     "asl": "QUESTION I HAVE",
     "category": "work",
     "augmented": ["i have a question", "i have a quick question", "may i ask a question"]},

    {"english": "i am busy",
     "asl": "BUSY I",
     "category": "work",
     "augmented": ["i am busy", "i'm busy", "i'm really busy right now"]},

    # ── TRANSPORTATION ────────────────────────────────────────────────────────

    {"english": "where is the bus stop",
     "asl": "BUS-STOP WHERE",
     "category": "transport",
     "augmented": ["where is the bus stop", "where can i catch the bus",
                   "where is the nearest bus stop"]},

    {"english": "where is the train station",
     "asl": "TRAIN-STATION WHERE",
     "category": "transport",
     "augmented": ["where is the train station", "where is the metro", "where is the subway"]},

    {"english": "how do i get to {PLACE}",
     "asl": "{PLACE} HOW GET",
     "category": "transport",
     "augmented": ["how do i get to downtown", "how do i get to the airport",
                   "how do i get to the hospital"]},

    {"english": "i need a taxi",
     "asl": "TAXI I NEED",
     "category": "transport",
     "augmented": ["i need a taxi", "i need a cab", "can you call a taxi"]},

    {"english": "i missed the bus",
     "asl": "BUS MISS I",
     "category": "transport",
     "augmented": ["i missed the bus", "i missed my bus", "missed the bus"]},

    {"english": "does this bus go to {PLACE}",
     "asl": "{PLACE} THIS BUS GO",
     "category": "transport",
     "augmented": ["does this bus go to downtown", "does this bus go to the airport",
                   "does this bus go to the station"]},

    {"english": "i am driving to {PLACE}",
     "asl": "{PLACE} DRIVE I",
     "category": "transport",
     "augmented": ["i am driving to work", "i am driving to the store", "i am driving home"]},

    {"english": "the traffic is bad",
     "asl": "TRAFFIC BAD",
     "category": "transport",
     "augmented": ["the traffic is bad", "traffic is terrible", "there's a lot of traffic"]},
]


import re as _re


def _specificity(p: Pattern) -> int:
    """Sort key: more literal (non-slot) words = higher specificity = sorts first.

    This ensures "i need a doctor" (literal=4) fires before "i need {THING}" (literal=2),
    "i am allergic to {THING}" (literal=4) fires before "i am {ADJECTIVE}" (literal=2), etc.
    Tie-breaking preserves original insertion order (Python sort is stable).
    """
    english = p["english"]
    total = len(english.split())
    slots = len(_re.findall(r"\{[^}]+\}", english))
    return -(total - slots)   # negative → descending sort by literal word count


PATTERNS.sort(key=_specificity)


def get_patterns_by_category(category: str) -> list[Pattern]:
    return [p for p in PATTERNS if p["category"] == category]


def get_all_augmented_examples() -> list[tuple[str, str]]:
    """Return all (english_example, asl_gloss) pairs from augmented examples.

    For patterns without slots, the asl is the direct gloss.
    For patterns with slots, the asl from augmented examples is the direct gloss
    (not template — the template is used for slot-based runtime matching).
    """
    examples: list[tuple[str, str]] = []
    for pattern in PATTERNS:
        for example in pattern["augmented"]:
            examples.append((example, pattern["asl"]))
    return examples


def get_all_patterns_for_index() -> list[tuple[str, str, str]]:
    """Return (english_example, asl_gloss, pattern_english) tuples for FAISS indexing."""
    result: list[tuple[str, str, str]] = []
    for pattern in PATTERNS:
        for example in pattern["augmented"]:
            result.append((example, pattern["asl"], pattern["english"]))
    return result
