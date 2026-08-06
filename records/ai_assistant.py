"""
Multilingual AI assistant: answers a patient's questions about their OWN
structured record, translating/explaining in their preferred language.

This intentionally works over STRUCTURED data (the patient's actual record),
not open-domain retrieval - which is simpler, faster to build, and more
reliable than general RAG for this specific use case: we always know exactly
what data the answer should be grounded in.

Set GROQ_API_KEY or OPENAI_API_KEY as an environment variable to enable live
LLM responses. Without a key, a rule-based fallback still answers common
questions IN THE PATIENT'S CHOSEN LANGUAGE, so the demo stays multilingual
even fully offline.
"""
import os

LANGUAGE_NAMES = {
    "en": "English", "hi": "Hindi", "ml": "Malayalam",
    "bn": "Bengali", "or": "Odia", "as": "Assamese",
}

# Native-script name for each language, used to reinforce the instruction to
# smaller/faster models that sometimes default to English or Hindi despite
# being told the language name in English - seeing the language's own script
# name makes the instruction much harder to ignore.
LANGUAGE_NATIVE_NAMES = {
    "en": "English", "hi": "हिन्दी (Hindi)", "ml": "മലയാളം (Malayalam)",
    "bn": "বাংলা (Bengali)", "or": "ଓଡ଼ିଆ (Odia)", "as": "অসমীয়া (Assamese)",
}

# Offline fallback templates, per language, so the demo stays multilingual
# even with zero API keys configured.
FALLBACK_TEMPLATES = {
    "en": {
        "medication": "[Offline mode] Based on your last visit ({date}): {meds}",
        "medication_none": "[Offline mode] No medication records found yet.",
        "followup": "[Offline mode] Your next follow-up is on {date}.",
        "followup_none": "[Offline mode] No follow-up date is currently scheduled.",
        "condition": "[Offline mode] Your recorded conditions: {conditions}",
        "default": "[Offline mode] I can answer questions about your medications, "
                    "conditions, and follow-up dates. Please ask clinic staff for anything else.",
    },
    "hi": {
        "medication": "[ऑफ़लाइन मोड] आपकी पिछली विज़िट ({date}) के अनुसार: {meds}",
        "medication_none": "[ऑफ़लाइन मोड] अभी तक कोई दवा रिकॉर्ड नहीं मिला।",
        "followup": "[ऑफ़लाइन मोड] आपकी अगली फॉलो-अप तारीख {date} है।",
        "followup_none": "[ऑफ़लाइन मोड] फिलहाल कोई फॉलो-अप तारीख निर्धारित नहीं है।",
        "condition": "[ऑफ़लाइन मोड] आपकी दर्ज स्थितियां: {conditions}",
        "default": "[ऑफ़लाइन मोड] मैं आपकी दवाओं, स्थितियों और फॉलो-अप तारीखों के बारे में सवालों के जवाब दे सकता हूं। "
                    "कृपया अन्य जानकारी के लिए क्लिनिक स्टाफ से पूछें।",
    },
    "bn": {
        "medication": "[অফলাইন মোড] আপনার শেষ ভিজিট ({date}) অনুযায়ী: {meds}",
        "medication_none": "[অফলাইন মোড] এখনও কোনো ওষুধের রেকর্ড পাওয়া যায়নি।",
        "followup": "[অফলাইন মোড] আপনার পরবর্তী ফলো-আপ {date} তারিখে।",
        "followup_none": "[অফলাইন মোড] বর্তমানে কোনো ফলো-আপ তারিখ নির্ধারিত নেই।",
        "condition": "[অফলাইন মোড] আপনার নথিভুক্ত অবস্থা: {conditions}",
        "default": "[অফলাইন মোড] আমি আপনার ওষুধ, অবস্থা এবং ফলো-আপ তারিখ সম্পর্কে প্রশ্নের উত্তর দিতে পারি। "
                   "অন্য কিছুর জন্য ক্লিনিক স্টাফকে জিজ্ঞাসা করুন।",
    },
    "ml": {
        "medication": "[ഓഫ്‌ലൈൻ മോഡ്] നിങ്ങളുടെ അവസാന സന്ദർശനം ({date}) പ്രകാരം: {meds}",
        "medication_none": "[ഓഫ്‌ലൈൻ മോഡ്] ഇതുവരെ മരുന്ന് രേഖകളൊന്നും കണ്ടെത്തിയില്ല.",
        "followup": "[ഓഫ്‌ലൈൻ മോഡ്] നിങ്ങളുടെ അടുത്ത ഫോളോ-അപ്പ് {date} ന് ആണ്.",
        "followup_none": "[ഓഫ്‌ലൈൻ മോഡ്] നിലവിൽ ഫോളോ-അപ്പ് തീയതി നിശ്ചയിച്ചിട്ടില്ല.",
        "condition": "[ഓഫ്‌ലൈൻ മോഡ്] രേഖപ്പെടുത്തിയ അവസ്ഥകൾ: {conditions}",
        "default": "[ഓഫ്‌ലൈൻ മോഡ്] മരുന്നുകൾ, അവസ്ഥകൾ, ഫോളോ-അപ്പ് തീയതികൾ എന്നിവയെക്കുറിച്ചുള്ള ചോദ്യങ്ങൾക്ക് എനിക്ക് ഉത്തരം നൽകാം. "
                    "മറ്റെന്തിനും ദയവായി ക്ലിനിക് സ്റ്റാഫിനോട് ചോദിക്കുക.",
    },
    "or": {
        "medication": "[ଅଫଲାଇନ୍ ମୋଡ୍] ଆପଣଙ୍କର ଶେଷ ପରିଦର୍ଶନ ({date}) ଅନୁଯାୟୀ: {meds}",
        "medication_none": "[ଅଫଲାଇନ୍ ମୋଡ୍] ଏପର୍ଯ୍ୟନ୍ତ କୌଣସି ଔଷଧ ରେକର୍ଡ ମିଳିଲା ନାହିଁ।",
        "followup": "[ଅଫଲାଇନ୍ ମୋଡ୍] ଆପଣଙ୍କର ପରବର୍ତ୍ତୀ ଫଲୋ-ଅପ୍ {date} ରେ ଅଛି।",
        "followup_none": "[ଅଫଲାଇନ୍ ମୋଡ୍] ବର୍ତ୍ତମାନ କୌଣସି ଫଲୋ-ଅପ୍ ତାରିଖ ନିର୍ଧାରିତ ନାହିଁ।",
        "condition": "[ଅଫଲାଇନ୍ ମୋଡ୍] ଆପଣଙ୍କର ରେକର୍ଡ ହୋଇଥିବା ଅବସ୍ଥା: {conditions}",
        "default": "[ଅଫଲାଇନ୍ ମୋଡ୍] ମୁଁ ଔଷଧ, ଅବସ୍ଥା ଏବଂ ଫଲୋ-ଅପ୍ ତାରିଖ ବିଷୟରେ ପ୍ରଶ୍ନର ଉତ୍ତର ଦେଇପାରିବି। "
                    "ଅନ୍ୟ କିଛି ପାଇଁ ଦୟାକରି କ୍ଲିନିକ୍ କର୍ମଚାରୀଙ୍କୁ ପଚାରନ୍ତୁ।",
    },
    "as": {
        "medication": "[অফলাইন ম'ড] আপোনাৰ যোৱা ভিজিট ({date}) অনুসৰি: {meds}",
        "medication_none": "[অফলাইন ম'ড] এতিয়ালৈকে কোনো ঔষধৰ ৰেকৰ্ড পোৱা নাযায়।",
        "followup": "[অফলাইন ম'ড] আপোনাৰ পৰৱৰ্তী ফলো-আপ {date} তাৰিখে।",
        "followup_none": "[অফলাইন ম'ড] বৰ্তমান কোনো ফলো-আপ তাৰিখ নিৰ্ধাৰিত নাই।",
        "condition": "[অফলাইন ম'ড] আপোনাৰ লিপিবদ্ধ অৱস্থা: {conditions}",
        "default": "[অফলাইন ম'ড] মই আপোনাৰ ঔষধ, অৱস্থা আৰু ফলো-আপ তাৰিখৰ বিষয়ে প্ৰশ্নৰ উত্তৰ দিব পাৰোঁ। "
                    "অন্য যিকোনো বিষয়ৰ বাবে অনুগ্ৰহ কৰি ক্লিনিক কৰ্মচাৰীক সোধক।",
    },
}


def build_patient_context(patient):
    """Turns the patient's DB record into a clean text block for the LLM prompt."""
    latest_visits = patient.visits.all()[:3]
    visits_text = "\n".join(
        f"- {v.visit_date} at {v.clinic_name}: {v.diagnosis}. "
        f"Medications: {v.medications_prescribed}. "
        f"Follow-up: {v.follow_up_date or 'None scheduled'}"
        for v in latest_visits
    ) or "No visit history recorded yet."

    return f"""
Patient name: {patient.full_name}
Known conditions: {patient.known_conditions or 'None recorded'}
Known allergies: {patient.known_allergies or 'None recorded'}
Recent visits:
{visits_text}
""".strip()


def _call_llm(system_prompt, user_question):
    """Calls Groq (fast + free tier) if configured, else OpenAI, else None."""
    groq_key = os.environ.get("GROQ_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")

    if groq_key:
        try:
            from groq import Groq
            client = Groq(api_key=groq_key)
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_question},
                ],
                temperature=0.3,
            )
            return resp.choices[0].message.content
        except Exception as e:
            return f"[AI service error: {e}]"

    if openai_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_question},
                ],
                temperature=0.3,
            )
            return resp.choices[0].message.content
        except Exception as e:
            return f"[AI service error: {e}]"

    return None


def answer_patient_question(patient, question, language_override=None):
    """
    Main entry point. Returns (answer_text, is_offline_fallback) - the boolean
    lets the frontend badge correctly show online/offline status regardless
    of which language the fallback text is written in.
    """
    lang_code = language_override or patient.preferred_language
    lang_name = LANGUAGE_NAMES.get(lang_code, "English")
    lang_native = LANGUAGE_NATIVE_NAMES.get(lang_code, "English")
    context = build_patient_context(patient)

    system_prompt = f"""You are a calm, clear medical record assistant helping a migrant
worker understand their OWN health record.

CRITICAL LANGUAGE RULE - follow this exactly, it is the most important instruction:
- You MUST write your ENTIRE response in {lang_native}.
- Use the native script of that language (e.g. Malayalam script for Malayalam, Bengali
  script for Bengali) - NOT English letters, NOT a transliteration, NOT romanized text.
- Do NOT default to Hindi or English under any circumstance, even if the question
  itself was typed in English or a different language.
- If you are unsure how to say something in {lang_name}, do your best in {lang_name}
  anyway - do not switch languages.

OTHER RULES:
- Answer ONLY using the record data provided below - never invent medical information
- Use simple, non-technical language
- If the record doesn't contain the answer, say so honestly (in {lang_name}) and
  suggest they ask clinic staff
- Never diagnose new conditions or suggest new medications - you only explain existing records
- Keep answers short (2-4 sentences)

PATIENT RECORD:
{context}
"""

    llm_response = _call_llm(system_prompt, question)
    if llm_response:
        return llm_response, False

    # Fallback (no API key configured, or the API call failed) - rule-based
    # answers, correctly localized to the chosen language.
    t = FALLBACK_TEMPLATES.get(lang_code, FALLBACK_TEMPLATES["en"])
    q = question.lower()

    medication_keywords = [
        "medication", "medicine", "ওষুধ", "दवा", "മരുന്ന്", "ଔଷଧ", "ঔষধ",
        "ଦବା", "মেডিসিন",
    ]
    followup_keywords = [
        "follow", "next", "appointment", "checkup", "check-up", "check up",
        "ফলো", "চেকআপ", "পরবর্তী",
        "फॉलो", "चेकअप", "अगला",
        "ഫോളോ", "ചെക്കപ്പ്", "അടുത്ത",
        "ଫଲୋ", "ଚେକ୍ଆପ୍", "ପରବର୍ତ୍ତୀ",
    ]
    condition_keywords = [
        "condition", "diagnosis", "अवस्था", "বার্তা", "অবস্থা", "রোগ",
        "അവസ്ഥ", "ଅବସ୍ଥା", "রোগনির্ণয়",
    ]

    if any(k in q for k in medication_keywords):
        latest = patient.visits.first()
        if latest:
            return t["medication"].format(date=latest.visit_date, meds=latest.medications_prescribed), True
        return t["medication_none"], True

    if any(k in q for k in followup_keywords):
        latest = patient.visits.first()
        if latest and latest.follow_up_date:
            return t["followup"].format(date=latest.follow_up_date), True
        return t["followup_none"], True

    if any(k in q for k in condition_keywords):
        return t["condition"].format(conditions=patient.known_conditions or "—"), True

    return t["default"], True