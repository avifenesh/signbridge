#!/usr/bin/env python3
"""Generate patterns.json from categorized pattern definitions.

Organized by ASL grammar rule and conversational category.
Run: python3 scripts/generate_patterns.py
"""
import json
from pathlib import Path

PATTERNS: list[tuple[str, str]] = []

# ============================================================
# QUESTIONS
# ============================================================
PATTERNS += [
    # WH-questions (question word at end in ASL)
    ("How many {NOUN} do you have", "{NOUN} YOU HAVE HOW-MANY"),
    ("How much does {NOUN} cost", "{NOUN} COST HOW-MUCH"),
    ("How long will it take", "TIME HOW-LONG"),
    ("What is your {NOUN}", "YOUR {NOUN} WHAT"),
    ("What color is {NOUN}", "{NOUN} COLOR WHAT"),
    ("What happened to {NOUN}", "{NOUN} HAPPEN WHAT"),
    ("What does {NOUN} mean", "{NOUN} MEAN WHAT"),
    ("What did you do today", "TODAY YOU DO WHAT"),
    ("What are you doing", "NOW YOU DO WHAT"),
    ("Where is the {NOUN}", "{NOUN} WHERE"),
    ("Where did {PERSON} go", "{PERSON} GO WHERE"),
    ("Is that your {NOUN}", "THAT YOUR {NOUN}"),
    ("When did you {VERB}", "YOU {VERB} WHEN"),
    ("When will you {VERB}", "YOU {VERB} WHEN WILL"),
    ("Who is {NOUN}", "{NOUN} WHO"),
    ("How do you {VERB}", "YOU {VERB} HOW"),
    ("How was your {NOUN}", "YOUR {NOUN} HOW"),
    ("What do you {VERB}", "YOU {VERB} WHAT"),
    ("Where do you {VERB}", "YOU {VERB} WHERE"),
    ("Why do you {VERB}", "YOU {VERB} WHY"),
    ("Why did you {VERB}", "YOU {VERB} WHY"),
    # Yes/no questions
    ("Do you have {NOUN}", "{NOUN} YOU HAVE"),
    ("Do you want {NOUN}", "{NOUN} YOU WANT"),
    ("Do you like {NOUN}", "{NOUN} YOU LIKE"),
    ("Do you know {NOUN}", "{NOUN} YOU KNOW"),
    ("Do you remember {NOUN}", "{NOUN} YOU REMEMBER"),
    ("Do you understand", "UNDERSTAND YOU"),
    ("Do you {VERB}", "YOU {VERB}"),
    ("Did you {VERB}", "YOU {VERB} FINISH"),
    ("Have you ever {VERB}", "YOU {VERB} EXPERIENCE"),
    ("Have you {VERB}", "YOU {VERB} FINISH"),
    ("Will you {VERB}", "YOU {VERB} WILL"),
    ("Are you {ADJECTIVE}", "YOU {ADJECTIVE}"),
    # Can you
    ("Can you help me with {NOUN}", "{NOUN} HELP ME CAN YOU"),
    ("Can you help me", "HELP ME CAN YOU"),
    ("Can you repeat that", "AGAIN PLEASE"),
    ("Can you show me {NOUN}", "{NOUN} SHOW ME CAN YOU"),
    ("Can you tell me about {NOUN}", "{NOUN} TELL ME CAN YOU"),
    ("Can you {VERB}", "YOU {VERB} CAN"),
    # Embedded questions
    ("Do you know where {NOUN} is", "{NOUN} WHERE YOU KNOW"),
    ("Do you know what time it is", "TIME WHAT YOU KNOW"),
    ("Can you tell me where {NOUN} is", "{NOUN} WHERE TELL ME CAN YOU"),
]

# ============================================================
# STATEMENTS — Transfer verbs (person + object)
# ============================================================
PATTERNS += [
    ("I gave {PERSON} the {OBJECT}", "{OBJECT} I GIVE-{PERSON}"),
    ("I told {PERSON} about {TOPIC}", "{TOPIC} I TELL-{PERSON}"),
    ("I showed {PERSON} the {OBJECT}", "{OBJECT} I SHOW-{PERSON}"),
    ("I asked {PERSON} about {TOPIC}", "{TOPIC} I ASK-{PERSON}"),
    ("I sent {PERSON} the {OBJECT}", "{OBJECT} I SEND-{PERSON}"),
    ("{PERSON} gave me the {OBJECT}", "{OBJECT} {PERSON} GIVE-ME"),
    ("{PERSON} told me about {TOPIC}", "{TOPIC} {PERSON} TELL-ME"),
    ("{PERSON} showed me the {OBJECT}", "{OBJECT} {PERSON} SHOW-ME"),
]

# ============================================================
# STATEMENTS — Relationships & identity
# ============================================================
PATTERNS += [
    ("{PERSON} is my {RELATION}", "{PERSON} MY {RELATION}"),
    ("My name is {NAME}", "MY NAME {NAME}"),
    ("My favorite {NOUN} is {NAME}", "MY FAVORITE {NOUN} {NAME}"),
    ("The {NOUN} is {ADJECTIVE}", "{NOUN} {ADJECTIVE}"),
    ("I am {NUMBER} years old", "AGE {NUMBER} I"),
    ("I have {NUMBER} {NOUN}", "{NOUN} {NUMBER} I HAVE"),
    ("There are {NUMBER} {NOUN}", "{NOUN} {NUMBER} THERE"),
]

# ============================================================
# STATEMENTS — Want / need / like / have (with "to VERB" before "OBJECT")
# ============================================================
PATTERNS += [
    ("I want to go to {PLACE}", "{PLACE} I WANT GO"),
    ("I want to {VERB}", "{VERB} I WANT"),
    ("I need to go to {PLACE}", "{PLACE} I NEED GO"),
    ("I need to {VERB}", "{VERB} I NEED"),
    ("I like to {VERB}", "{VERB} I LIKE"),
    ("I used to {VERB}", "BEFORE {VERB} I"),
    ("I know how to {VERB}", "{VERB} I KNOW HOW"),
    ("I learned to {VERB}", "{VERB} I LEARN FINISH"),
    ("I want {OBJECT}", "{OBJECT} I WANT"),
    ("I need {OBJECT}", "{OBJECT} I NEED"),
    ("I like {OBJECT}", "{OBJECT} I LIKE"),
    ("I love {OBJECT}", "{OBJECT} I LOVE"),
    ("I have {OBJECT}", "{OBJECT} I HAVE"),
    ("I prefer {OBJECT}", "{OBJECT} I PREFER"),
    ("I remember {NOUN}", "{NOUN} I REMEMBER"),
    ("I forgot {NOUN}", "{NOUN} I FORGET"),
]

# ============================================================
# STATEMENTS — Descriptions & states
# ============================================================
PATTERNS += [
    ("I am {ADJECTIVE}", "I {ADJECTIVE}"),
    ("I feel {ADJECTIVE}", "I FEEL {ADJECTIVE}"),
    ("{PERSON} is {ADJECTIVE}", "{PERSON} {ADJECTIVE}"),
    ("{PERSON} looks {ADJECTIVE}", "{PERSON} LOOK {ADJECTIVE}"),
    ("{PERSON} seems {ADJECTIVE}", "{PERSON} SEEM {ADJECTIVE}"),
]

# ============================================================
# STATEMENTS — Mental / opinion / intent
# ============================================================
PATTERNS += [
    ("I think {PERSON} is {ADJECTIVE}", "{PERSON} {ADJECTIVE} I THINK"),
    ("I think you should {VERB}", "{VERB} YOU SHOULD I THINK"),
    ("I think so", "THINK I YES"),
    ("I hope you {VERB}", "YOU {VERB} I HOPE"),
    ("I hope so", "HOPE I YES"),
    ("I wish I could {VERB}", "{VERB} I WISH"),
    ("I promise to {VERB}", "{VERB} I PROMISE"),
    ("I decided to {VERB}", "{VERB} I DECIDE"),
    ("I plan to {VERB}", "{VERB} I PLAN"),
    ("I tried to {VERB}", "{VERB} I TRY"),
    ("I started to {VERB}", "{VERB} I START"),
    ("I stopped {VERB}", "{VERB} I STOP"),
    ("I finished {VERB}", "{VERB} I FINISH"),
    ("I keep {VERB}", "{VERB} I CONTINUE"),
    ("I just {VERB}", "{VERB} I JUST FINISH"),
    ("I am going to {VERB}", "{VERB} I WILL"),
    ("I wonder if {PHRASE}", "{PHRASE} I WONDER"),
    ("I know that {PHRASE}", "{PHRASE} I KNOW"),
    ("I heard that {PHRASE}", "{PHRASE} I HEAR"),
    ("I believe {NOUN}", "{NOUN} I BELIEVE"),
    ("I agree with {PERSON}", "{PERSON} I AGREE"),
]

# ============================================================
# MODALS & ABILITY
# ============================================================
PATTERNS += [
    ("I can {VERB}", "{VERB} I CAN"),
    ("I should {VERB}", "{VERB} I SHOULD"),
    ("I must {VERB}", "{VERB} I MUST"),
    ("I might {VERB}", "{VERB} I MAYBE"),
    ("I could {VERB}", "{VERB} I COULD"),
    ("May I {VERB}", "{VERB} I MAY"),
    ("You should {VERB}", "{VERB} YOU SHOULD"),
    ("You must {VERB}", "{VERB} YOU MUST"),
    ("You can {VERB}", "{VERB} YOU CAN"),
    ("{PERSON} can {VERB}", "{PERSON} {VERB} CAN"),
    ("{PERSON} should {VERB}", "{PERSON} {VERB} SHOULD"),
    ("I am able to {VERB}", "{VERB} I CAN"),
    ("I am not able to {VERB}", "{VERB} I CAN'T"),
    ("I have to {VERB}", "{VERB} I MUST"),
    ("You have to {VERB}", "{VERB} YOU MUST"),
    ("We have to {VERB}", "{VERB} WE MUST"),
    ("I do not have to {VERB}", "{VERB} I MUST NOT"),
]

# ============================================================
# NEGATION (specific before general)
# ============================================================
PATTERNS += [
    ("I can not believe {PERSON} said that", "{PERSON} SAY THAT BELIEVE I CAN'T"),
    ("I do not have enough {NOUN}", "{NOUN} ENOUGH I HAVE NOT"),
    ("I do not have {OBJECT}", "{OBJECT} I HAVE NOT"),
    ("I do not want {OBJECT}", "{OBJECT} I WANT NOT"),
    ("I do not like {OBJECT}", "{OBJECT} I LIKE NOT"),
    ("I do not know {NOUN}", "{NOUN} I KNOW NOT"),
    ("I do not remember {NOUN}", "{NOUN} I REMEMBER NOT"),
    ("I do not understand {NOUN}", "{NOUN} UNDERSTAND I NOT"),
    ("I do not understand", "UNDERSTAND I NOT"),
    ("I do not care about {NOUN}", "{NOUN} I CARE NOT"),
    ("I do not think so", "THINK I NOT"),
    ("I do not agree", "AGREE I NOT"),
    ("I do not mind", "MIND I NOT"),
    ("I do not {VERB}", "{VERB} I NOT"),
    ("I can not {VERB}", "{VERB} I CAN'T"),
    ("I will not {VERB}", "{VERB} I WILL NOT"),
    ("I have never {VERB}", "{VERB} I NEVER"),
    ("{PERSON} does not {VERB}", "{PERSON} {VERB} NOT"),
    ("{PERSON} did not {VERB}", "{PERSON} {VERB} NOT"),
    ("There is no {NOUN}", "{NOUN} NONE"),
    ("I have no {NOUN}", "{NOUN} I HAVE NONE"),
    ("Nobody {VERB}", "{VERB} NOBODY"),
    ("Nothing happened", "HAPPEN NOTHING"),
]

# ============================================================
# THIRD-PERSON STATEMENTS
# ============================================================
PATTERNS += [
    ("{PERSON} wants {OBJECT}", "{OBJECT} {PERSON} WANT"),
    ("{PERSON} needs {OBJECT}", "{OBJECT} {PERSON} NEED"),
    ("{PERSON} likes {OBJECT}", "{OBJECT} {PERSON} LIKE"),
    ("{PERSON} has {OBJECT}", "{OBJECT} {PERSON} HAVE"),
    ("{PERSON} went to {PLACE}", "{PLACE} {PERSON} GO FINISH"),
    ("{PERSON} works at {PLACE}", "{PLACE} {PERSON} WORK"),
    ("{PERSON} lives in {PLACE}", "{PERSON} {PLACE} LIVE"),
    ("{PERSON} said {PHRASE}", "{PERSON} SAY {PHRASE}"),
    ("{PERSON} already {VERB}", "{PERSON} {VERB} FINISH"),
]

# ============================================================
# PAST TENSE / EXPERIENCE
# ============================================================
PATTERNS += [
    ("I went to {PLACE}", "{PLACE} I GO FINISH"),
    ("I came from {PLACE}", "{PLACE} I COME-FROM"),
    ("I saw {NOUN}", "{NOUN} I SEE FINISH"),
    ("I met {PERSON} at {PLACE}", "{PLACE} {PERSON} I MEET"),
    ("I already {VERB}", "{VERB} I FINISH"),
    ("I have been to {PLACE}", "{PLACE} I GO FINISH"),
    ("I have never been to {PLACE}", "{PLACE} I GO NEVER"),
    ("I was {ADJECTIVE}", "BEFORE I {ADJECTIVE}"),
]

# ============================================================
# TIME EXPRESSIONS
# ============================================================
PATTERNS += [
    ("Yesterday I {VERB}", "YESTERDAY I {VERB}"),
    ("Tomorrow I will {VERB}", "TOMORROW I {VERB}"),
    ("I will {VERB} tomorrow", "TOMORROW I {VERB}"),
    ("Last week I {VERB}", "LAST-WEEK I {VERB}"),
    ("Next week I will {VERB}", "NEXT-WEEK I {VERB}"),
    ("Every day I {VERB}", "EVERY-DAY I {VERB}"),
    ("Sometimes I {VERB}", "SOMETIMES I {VERB}"),
    ("I always {VERB}", "ALWAYS I {VERB}"),
    ("I never {VERB}", "{VERB} I NEVER"),
    ("I usually {VERB}", "USUALLY I {VERB}"),
    ("Right now I am {VERB}", "NOW I {VERB}"),
    ("Later I will {VERB}", "LATER I {VERB}"),
    ("Soon I will {VERB}", "SOON I {VERB}"),
    ("I {VERB} every morning", "EVERY MORNING I {VERB}"),
    ("I {VERB} at night", "NIGHT I {VERB}"),
]

# ============================================================
# LOCATION & DIRECTION
# ============================================================
PATTERNS += [
    ("I am at {PLACE}", "{PLACE} I HERE"),
    ("I am going to {PLACE}", "{PLACE} I GO"),
    ("I live in {PLACE}", "{PLACE} I LIVE"),
    ("I work at {PLACE}", "{PLACE} I WORK"),
    ("It is near {PLACE}", "{PLACE} NEAR"),
    ("It is far from {PLACE}", "{PLACE} FAR"),
    ("I am from {PLACE}", "{PLACE} I FROM"),
    ("{NOUN} is over there", "{NOUN} THERE"),
    ("{NOUN} is here", "{NOUN} HERE"),
]

# ============================================================
# EMOTIONS & PHYSICAL STATES (fixed phrases, high specificity)
# ============================================================
PATTERNS += [
    ("I am hungry", "I HUNGRY"),
    ("I am thirsty", "I THIRSTY"),
    ("I am tired", "I TIRED"),
    ("I am sick", "I SICK"),
    ("I am happy", "I HAPPY"),
    ("I am sad", "I SAD"),
    ("I am angry", "I ANGRY"),
    ("I am scared", "I SCARED"),
    ("I am excited", "I EXCITED"),
    ("I am nervous", "I NERVOUS"),
    ("I am confused", "I CONFUSED"),
    ("I am bored", "I BORED"),
    ("I am surprised", "I SURPRISED"),
    ("I am worried about {NOUN}", "{NOUN} I WORRIED"),
    ("I am proud of {PERSON}", "{PERSON} I PROUD"),
    ("I am sorry about {NOUN}", "{NOUN} I SORRY"),
    ("I am ready", "I READY"),
    ("I am not ready", "READY I NOT"),
]

# ============================================================
# COMPARISON
# ============================================================
PATTERNS += [
    ("{NOUN} is better than {OTHER}", "{NOUN} {OTHER} COMPARE {NOUN} BETTER"),
    ("{NOUN} is the same as {OTHER}", "{NOUN} {OTHER} SAME"),
    ("{NOUN} is different from {OTHER}", "{NOUN} {OTHER} DIFFERENT"),
    ("I am the same as {PERSON}", "{PERSON} I SAME"),
    ("{NOUN} is the best", "{NOUN} BEST"),
    ("This is more {ADJECTIVE} than that", "THIS THAT COMPARE THIS MORE {ADJECTIVE}"),
]

# ============================================================
# CAUSAL / CONDITIONAL
# ============================================================
PATTERNS += [
    ("If you want I can {VERB}", "YOU WANT I {VERB} CAN"),
    ("If you need help with {NOUN}", "{NOUN} HELP YOU NEED IF"),
    ("Because of {NOUN}", "{NOUN} BECAUSE"),
    ("That is why I {VERB}", "I {VERB} WHY THAT"),
    ("Maybe we should {VERB}", "MAYBE {VERB} WE SHOULD"),
    ("We should {VERB}", "{VERB} WE SHOULD"),
    ("We can {VERB} together", "TOGETHER {VERB} WE CAN"),
    ("Let us {VERB}", "{VERB} WE"),
    ("That is a good {NOUN}", "{NOUN} GOOD"),
]

# ============================================================
# REQUESTS & COMMANDS
# ============================================================
PATTERNS += [
    ("Please help me with {NOUN}", "{NOUN} HELP ME PLEASE"),
    ("Please tell me about {NOUN}", "{NOUN} TELL ME PLEASE"),
    ("Please wait for me", "ME WAIT PLEASE"),
    ("Please give me {OBJECT}", "{OBJECT} GIVE-ME PLEASE"),
    ("Please {VERB}", "PLEASE {VERB}"),
    ("Tell me about {NOUN}", "{NOUN} TELL ME"),
    ("Show me {NOUN}", "{NOUN} SHOW ME"),
    ("Give me {OBJECT}", "{OBJECT} GIVE-ME"),
    ("I have a question", "QUESTION I HAVE"),
    ("I have something to tell you", "SOMETHING TELL-YOU I HAVE"),
]

# ============================================================
# DAILY LIFE
# ============================================================
PATTERNS += [
    ("I am going home", "HOME I GO"),
    ("I am at home", "HOME I HERE"),
    ("I need to go home", "HOME GO I NEED"),
    ("I ate {NOUN}", "{NOUN} I EAT FINISH"),
    ("I bought {NOUN}", "{NOUN} I BUY FINISH"),
    ("I made {NOUN}", "{NOUN} I MAKE FINISH"),
    ("I found {NOUN}", "{NOUN} I FIND FINISH"),
    ("I lost {NOUN}", "{NOUN} I LOSE"),
    ("I broke {NOUN}", "{NOUN} I BREAK"),
    ("I fixed {NOUN}", "{NOUN} I FIX FINISH"),
    ("I paid for {NOUN}", "{NOUN} I PAY FINISH"),
    ("I am looking for {NOUN}", "{NOUN} I LOOK-FOR"),
    ("I am waiting for {PERSON}", "{PERSON} I WAIT"),
]

# ============================================================
# SOCIAL / GREETINGS / FIXED PHRASES
# ============================================================
PATTERNS += [
    ("How are you", "YOU HOW"),
    ("What time is it", "TIME WHAT"),
    ("Hello", "HELLO"),
    ("Hi", "HELLO"),
    ("Good morning", "GOOD MORNING"),
    ("Good afternoon", "GOOD AFTERNOON"),
    ("Good evening", "GOOD EVENING"),
    ("Good night", "GOOD NIGHT"),
    ("Goodbye", "GOODBYE"),
    ("Bye", "GOODBYE"),
    ("Thank you very much", "THANK-YOU VERY-MUCH"),
    ("Thank you", "THANK-YOU"),
    ("Thanks", "THANK-YOU"),
    ("You are welcome", "WELCOME"),
    ("I am sorry", "SORRY"),
    ("Sorry", "SORRY"),
    ("Yes", "YES"),
    ("No", "NO"),
    ("Maybe", "MAYBE"),
    ("Of course", "OF-COURSE"),
    ("I agree", "AGREE"),
    ("Nice to meet you", "MEET YOU NICE"),
    ("Long time no see", "LONG-TIME SEE NOT"),
    ("I understand", "I UNDERSTAND"),
    ("I see", "I UNDERSTAND"),
    ("That is interesting", "INTERESTING"),
    ("That is funny", "FUNNY"),
    ("Really", "REALLY"),
    ("Wait a moment", "WAIT"),
    ("Hold on", "WAIT"),
    ("One moment", "WAIT"),
    ("Excuse me", "EXCUSE"),
    ("I love you", "I LOVE YOU"),
    ("I miss you", "I MISS YOU"),
    ("See you later", "LATER SEE YOU"),
    ("See you tomorrow", "TOMORROW SEE YOU"),
    ("I have to go now", "NOW GO I MUST"),
    ("I have to go", "GO I MUST"),
    ("Take care", "TAKE-CARE"),
    ("Be careful", "CAREFUL"),
    ("No problem", "NO-PROBLEM"),
    ("It is okay", "OKAY"),
    ("That sounds good", "GOOD"),
    ("I am fine", "I FINE"),
    ("I am okay", "I OKAY"),
    ("I am busy right now", "NOW I BUSY"),
    ("I am free right now", "NOW I FREE"),
    ("I will be there", "THERE I WILL"),
    ("I will call you back", "LATER I CALL YOU"),
    ("The weather is nice today", "TODAY WEATHER NICE"),
    ("The weather is nice", "TODAY WEATHER NICE"),
    ("Let us talk", "TALK WE"),
    ("What do you think", "YOU THINK WHAT"),
    ("I have no idea", "I KNOW NOT"),
    ("That is right", "RIGHT"),
    ("That is wrong", "WRONG"),
    ("I was wrong", "I WRONG"),
    ("You are right", "YOU RIGHT"),
    ("It does not matter", "MATTER NOT"),
    ("Never mind", "NEVER-MIND"),
    ("Congratulations", "CONGRATULATIONS"),
    ("Happy birthday", "HAPPY BIRTHDAY"),
    ("I am just kidding", "I JOKE"),
    ("Are you serious", "YOU SERIOUS"),
    ("I am serious", "I SERIOUS"),
    ("Me too", "ME SAME"),
    ("Same here", "SAME"),
]


def main() -> None:
    out = [{"pattern": p, "asl_template": t} for p, t in PATTERNS]
    path = Path(__file__).resolve().parent.parent / "data" / "patterns.json"
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print(f"Generated {len(out)} patterns → {path}")


if __name__ == "__main__":
    main()
