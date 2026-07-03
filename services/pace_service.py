def build_pace(months_next, months_full):

    if months_next is None:
        return {
            "pace": "⚠️ No monthly contribution",
            "months_next": None,
            "months_full": months_full,
        }

    if months_next <= 1:
        pace = "🚀 Excellent"

    elif months_next <= 6:
        pace = "✅ On Track"

    elif months_next <= 12:
        pace = "🙂 Steady"

    else:
        pace = "🐢 Slow"

    return {
        "pace": pace,
        "months_next": months_next,
        "months_full": months_full,
    }


def build_nudge(months_next):

    if months_next is None:
        return "Add a monthly contribution to receive pace guidance."

    if months_next <= 1:
        return "🎉 You're almost at your next milestone!"

    elif months_next <= 6:
        return "💡 Keep saving consistently."

    elif months_next <= 12:
        return "📈 Increase your monthly contribution to unlock the next milestone sooner."

    else:
        return "🚀 Consider increasing your monthly savings to speed up your dream."