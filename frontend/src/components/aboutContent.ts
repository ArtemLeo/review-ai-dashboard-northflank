/** Languages the "About" dialog is available in. */
export type AboutLocale = "uk" | "en";

/**
 * Line icons of the feature cards, drawn in the same 24×24 stroke style as
 * the other icons of the app. Each entry is the list of SVG path outlines.
 */
export const FEATURE_ICONS = {
  // The robot head of the review details dialog, moved down to sit centred.
  bot: [
    "M4 7h16a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2z",
    "M7 11h.01",
    "M17 11h.01",
    "M7 7V5",
    "M17 7V5",
    "M9 16h6",
  ],
  pen: ["M12 21h9", "M16.5 4a2.12 2.12 0 0 1 3 3L7 19.5l-4 1 1-4z"],
  alert: [
    "M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z",
    "M12 9v4",
    "M12 17h.01",
  ],
  clock: ["M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20z", "M12 6v6l4 2"],
  // Globe: a circle with the equator and one meridian.
  globe: [
    "M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20z",
    "M2 12h20",
    "M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z",
  ],
  // Crossed-out bell: an alert nobody hears.
  bellOff: [
    "M13.73 21a2 2 0 0 1-3.46 0",
    "M18.63 13A17.89 17.89 0 0 1 18 8",
    "M6.26 6.26A5.86 5.86 0 0 0 6 8c0 7-3 9-3 9h14",
    "M18 8a6 6 0 0 0-9.33-5",
    "M2 2l20 20",
  ],
  chart: ["M12 20V10", "M18 20V4", "M6 20v-4"],
  pointer: ["M3.5 3.5l7 17 2.5-7.5 7.5-2.5z", "M13 13l6 6"],
} as const;

/** Name of a feature card icon. */
type FeatureIcon = keyof typeof FEATURE_ICONS;

interface AboutItem {
  title: string;
  text: string;
}

/** Every text of the "About" dialog in one language. */
interface AboutContent {
  title: string;
  subtitle: string;
  lead: string;
  problemTitle: string;
  problems: (AboutItem & { icon: FeatureIcon })[];
  featuresTitle: string;
  features: (AboutItem & { icon: FeatureIcon })[];
  stepsTitle: string;
  steps: AboutItem[];
  businessTitle: string;
  business: string[];
  stackTitle: string;
  /** Accessible names of the icon-only controls. */
  languageLabel: string;
  scrollLabel: string;
  closeLabel: string;
}

/** Technology badges; product names read the same in every language. */
export const ABOUT_STACK = [
  "Vue 3",
  "TypeScript",
  "FastAPI",
  "PostgreSQL",
  "Celery + Redis",
  "Groq · Gemini",
  "Docker",
  "Nginx",
] as const;

/** Texts of the "About" dialog, condensed from README.md. */
export const ABOUT_CONTENT: Record<AboutLocale, AboutContent> = {
  uk: {
    title: "Про проєкт Review AI",
    subtitle: "Форма відгуків і панель AI-аналітики",
    lead:
      "Відвідувачі надсилають відгук через коротку форму. AI аналізує мову, оцінку, " +
      "категорію та терміновість, а оператор отримує чергу з чернеткою відповіді.",
    problemTitle: "Завдання",
    problems: [
      {
        icon: "clock",
        title: "Повільні відповіді",
        text: "Звернення складно опрацьовувати вручну та вчасно.",
      },
      { icon: "globe", title: "Різні мови", text: "Відгуки надходять різними мовами." },
      {
        icon: "bellOff",
        title: "Термінові звернення",
        text: "Важливі проблеми легко губляться в загальній черзі.",
      },
    ],
    featuresTitle: "Можливості",
    features: [
      {
        icon: "bot",
        title: "AI-аналіз",
        text: "Мова, оцінка, категорія та пріоритет кожного відгуку.",
      },
      {
        icon: "pen",
        title: "Чернетки відповідей",
        text: "Коротка відповідь мовою автора відгуку.",
      },
      {
        icon: "alert",
        title: "Термінові відгуки",
        text: "Оператор бачить звернення з високою терміновістю.",
      },
      { icon: "chart", title: "Аналітика", text: "Розподіл оцінок, фільтри та експорт CSV." },
      {
        icon: "pointer",
        title: "Робота з чергою",
        text: "Копіювання й оновлення AI-чернетки, зміна статусу.",
      },
    ],
    stepsTitle: "Як це працює",
    steps: [
      { title: "Надіслати відгук", text: "Вказати ім’я, email і текст звернення." },
      { title: "Аналіз", text: "Фоновий обробник надсилає відгук вибраному AI-провайдеру." },
      { title: "Відповісти", text: "Оператор перевіряє чергу та використовує чернетку відповіді." },
    ],
    businessTitle: "Обробка даних",
    business: [
      "Форма перевіряє обов’язкові поля та надсилає відгук до API.",
      "Відгуки зберігаються в PostgreSQL і потрапляють у чергу через Redis та Celery.",
      "Ключі AI-провайдерів і налаштування задаються через змінні середовища.",
    ],
    stackTitle: "Технології",
    languageLabel: "Мова",
    scrollLabel: "Прокрутити вниз",
    closeLabel: "Закрити",
  },
  en: {
    title: "About Review AI",
    subtitle: "A review form and AI analysis dashboard",
    lead:
      "Visitors submit feedback through a short form. AI analyses its language, rating, " +
      "category and urgency, then gives operators a queue with a draft reply.",
    problemTitle: "The challenge",
    problems: [
      {
        icon: "clock",
        title: "Slow replies",
        text: "Incoming messages are difficult to triage by hand.",
      },
      { icon: "globe", title: "Different languages", text: "Reviews arrive in many languages." },
      {
        icon: "bellOff",
        title: "Urgent reports",
        text: "Important issues can get lost in a busy queue.",
      },
    ],
    featuresTitle: "Features",
    features: [
      {
        icon: "bot",
        title: "AI analysis",
        text: "Language, rating, category and priority for each review.",
      },
      {
        icon: "pen",
        title: "Reply drafts",
        text: "A concise response in the review author's language.",
      },
      {
        icon: "alert",
        title: "Urgent reviews",
        text: "High urgency reports stand out to operators.",
      },
      { icon: "chart", title: "Analytics", text: "Rating distribution, filters and CSV export." },
      {
        icon: "pointer",
        title: "Queue workflow",
        text: "Copy or regenerate drafts and update review status.",
      },
    ],
    stepsTitle: "How it works",
    steps: [
      { title: "Submit feedback", text: "Enter a name, email and review." },
      {
        title: "Analyse",
        text: "A background worker sends the review to the configured AI provider.",
      },
      { title: "Respond", text: "An operator reviews the queue and uses the suggested draft." },
    ],
    businessTitle: "Data handling",
    business: [
      "The form validates required fields and sends reviews to the API.",
      "Reviews are stored in PostgreSQL and queued through Redis and Celery.",
      "AI provider keys and settings are supplied through environment variables.",
    ],
    stackTitle: "Built with",
    languageLabel: "Language",
    scrollLabel: "Scroll down",
    closeLabel: "Close",
  },
};
