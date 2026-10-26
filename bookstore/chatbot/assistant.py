from dataclasses import asdict

from bookstore import config
from bookstore.chatbot.llm import GeminiProvider
from bookstore.chatbot.tools import DashboardTools, DataTools, ValueClassifier
from bookstore.chatbot.verifier import find_unverified
from bookstore.cleaning.parsing import EUR_TO_USD

INSTRUCTIONS = """You are the analytics assistant of a bookstore dashboard. Stores: {stores}.
Each message starts with the store the dashboard shows; use it unless the user names another store.
For several stores call the tools once per store and compare the results with calculate.
Tables: {schema}.
Meaning: money is USD (EUR converted at {eur_rate}); currency = original currency; state = US state code;
timestamp = order time; date = 'YYYY-MM-DD' text (compare as text, e.g. date >= '2025-09-01');
year, month (1-12), day = numbers; year_month = 'YYYY-MM'; real_user = the real person behind several user ids
(aliases, changed address/phone/e-mail); "unique users" = distinct real_user; author_set = the set of co-authors.
RULES
1. Your ONLY source of information is the tool results. Never use general knowledge about books, authors, people
   or the world, and never invent or estimate data.
2. Never count, sum or calculate yourself. Every number must come from a tool; use calculate for arithmetic.
3. If you are unsure of the exact values in a column (e.g. genre names), look them up first with query(group_by=...).
4. If the tables cannot answer the question, say plainly that the store data does not contain it.
5. Dashboard commands use the DASHBOARD tools: "select/show X" = keep X, "filter out/remove/hide X" = exclude=True,
   "of those / now only / also" = narrow=True. Then report rows shown and 2-3 examples.
6. For trends over time group by year_month (or date) and sort_by the same column, ascending=True.
7. Answer briefly in the user's language and quote numbers exactly as the tools returned them."""

CORRECTION = ("These numbers in your answer are not in any tool result: {numbers}. "
              "Answer again using only numbers returned by the tools; call tools if you need more.")
WARNING = "\n\nWarning: not verified against the data: {numbers}"
NO_ANSWER = "Sorry, I could not finish this answer (too many steps). Please ask a narrower question."


class Assistant:
    def __init__(self, chat):
        self.chat = chat
        self.earlier_questions = []
        self.earlier_calls = []

    def check(self, answer, question, calls):
        results = [call.result for call in self.earlier_calls + calls]
        evidence = " ".join(self.earlier_questions + [question])
        return find_unverified(answer, evidence, results, known_numbers=[EUR_TO_USD])

    def remember(self, question, calls):
        self.earlier_questions.append(question)
        self.earlier_calls += calls

    def reply(self, store, question):
        first = self.chat.send(f"[Dashboard shows {store}] {question}")
        answer = first.text
        calls = list(first.tool_calls)
        unverified = self.check(answer, question, calls)

        if unverified:
            second = self.chat.send(CORRECTION.format(numbers=", ".join(unverified)))
            answer = second.text
            calls = calls + list(second.tool_calls)
            unverified = self.check(answer, question, calls)

        self.remember(question, calls)
        trace = [asdict(call) for call in calls]
        if answer.strip() == "":
            return NO_ANSWER, trace
        if unverified:
            answer = answer + WARNING.format(numbers=", ".join(unverified))
        return answer, trace


def gemini(api_key):
    return GeminiProvider(api_key, config.MODEL, config.MAX_TOOL_CALLS)


def build_assistant(stores, state, provider):
    classifier = ValueClassifier(provider.json_model(), config.CLASSIFIER_BATCH)
    data_tools = DataTools(stores, config.MAX_ROWS)
    dashboard_tools = DashboardTools(state, stores, classifier, config.EXAMPLE_ROWS)
    tools = data_tools.functions() + dashboard_tools.functions()

    names = stores.names()
    instructions = INSTRUCTIONS.format(stores=", ".join(names), schema=stores.get(names[0]).schema(),
                                       eur_rate=EUR_TO_USD)
    return Assistant(provider.chat(instructions, tools))
