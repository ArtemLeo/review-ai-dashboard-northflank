#!/usr/bin/env python3
"""Seed the database with 100 demo reviews from players of a CS2 case-opening skin platform.

Usage
-----
Normal run (idempotent — skips seeding if data already exists):
    python scripts/seed_database.py

Force re-seed (clears existing reviews and inserts fresh data):
    python scripts/seed_database.py --force

The container runs the normal mode at start when SEED_DEMO_DATA=true.
The script is safe to run multiple times without duplicating data.
"""

import random
import sys
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

# Ensure the backend directory is on Python path so app modules import cleanly
BACKEND_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import delete, func, select, text

from app.core.time import utcnow
from app.db.session import SessionLocal
from app.models.review import Review

# Sample data
FIRST_NAMES = [
    "Alex",
    "Maria",
    "John",
    "Sofia",
    "Dmitry",
    "Anna",
    "Carlos",
    "Yuki",
    "Hans",
    "Emma",
    "Lars",
    "Olga",
    "Pierre",
    "Mei",
    "Ahmed",
    "Sarah",
    "Viktor",
    "Natasha",
    "Luca",
    "Elena",
    "Kai",
    "Lin",
    "Mohammed",
    "Fatima",
    "Oleg",
    "Irina",
    "Stefan",
    "Helga",
    "Jin",
    "Haruto",
    "Andrei",
    "Ekaterina",
    "Felix",
    "Greta",
    "Hiroshi",
    "Ivan",
    "Julia",
    "Klaus",
    "Ling",
    "Max",
    "Nina",
    "Oscar",
    "Paula",
    "Quentin",
    "Rosa",
    "Sven",
    "Tatiana",
    "Uwe",
    "Vera",
    "Wei",
]

LAST_NAMES = [
    "Smith",
    "Johnson",
    "Williams",
    "Brown",
    "Jones",
    "Garcia",
    "Miller",
    "Davis",
    "Rodriguez",
    "Martinez",
    "Hernandez",
    "Lopez",
    "Gonzalez",
    "Wilson",
    "Anderson",
    "Thomas",
    "Taylor",
    "Moore",
    "Jackson",
    "Martin",
    "Lee",
    "Perez",
    "Thompson",
    "White",
    "Harris",
    "Sanchez",
    "Clark",
    "Ramirez",
    "Lewis",
    "Robinson",
    "Walker",
    "Young",
    "Allen",
    "King",
    "Wright",
    "Scott",
    "Torres",
    "Nguyen",
    "Hill",
    "Flores",
    "Green",
    "Adams",
    "Nelson",
    "Baker",
    "Hall",
    "Rivera",
    "Campbell",
    "Mitchell",
    "Carter",
    "Roberts",
]


@dataclass(frozen=True)
class DemoProfile:
    """What the simulated analysis says about one kind of demo review."""

    rating: int
    priority: str
    category: str
    needs_urgent_response: bool
    #: Key of the matching draft reply in :data:`DEMO_REPLIES`.
    reply: str


#: The kinds of demo reviews, from praise to the urgent complaints, so the
#: dashboard shows the whole range of what the analysis can say.
DEMO_PROFILES: dict[str, DemoProfile] = {
    "praise": DemoProfile(5, "Low", "Praise", False, "thanks"),  # enthusiastic praise
    "fan": DemoProfile(4, "Low", "Praise", False, "thanks"),  # praise with a small wish
    "idea": DemoProfile(4, "Medium", "FeatureRequest", False, "idea"),  # a feature request
    "glitch": DemoProfile(4, "Medium", "Bug", False, "sorry"),  # a minor bug on a good site
    "lag": DemoProfile(3, "Medium", "Bug", False, "sorry"),  # slow cases or withdrawals
    "question": DemoProfile(3, "Medium", "Support", False, "help"),  # a how-to question
    "toxic": DemoProfile(3, "Medium", "Other", False, "sorry"),  # a complaint about the battle chat
    "crash": DemoProfile(2, "High", "Bug", True, "sorry"),  # a feature of the site is broken
    "charge": DemoProfile(1, "High", "PaymentIssue", True, "sorry"),  # deposit or skin not received
    "ban": DemoProfile(1, "High", "Support", True, "sorry"),  # a locked account the player disputes
}

#: Player feedback about a CS2 case-opening and skin platform, by language
#: and kind, 100 in total and deliberately uneven: English 31,
#: Ukrainian 29, and 5 to 7 in each of the other seven languages.
DEMO_TEXTS: dict[str, dict[str, tuple[str, ...]]] = {
    "en": {
        "praise": (
            "Withdrew my AWP in under five minutes — the trade offer arrived before I even switched to Steam. Fastest skin site I've used so far.",
            "Finally a platform where the odds are actually published for every case. I checked a few openings with the provably fair tool and the hashes matched. Respect.",
            "The case opening animation is so smooth, even on my phone. The slow-down at the end with the glow on the rare item gives me chills every time.",
            "Support answered in the live chat in two minutes and fixed my trade link problem right away. Friendly and no copy-paste answers. 10/10.",
            "Pulled a knife from a mid-tier case on my third try today. Already withdrawn to my inventory, no trade hold drama. Best day ever!",
            "The daily free case is a nice touch. I log in every morning just for it, and twice it gave me skins worth more than a regular case.",
            "Case battles with friends are pure fun. We set up a 2v2 on Friday nights and the whole chat goes crazy when someone hits a covert.",
            "Deposited with a card and the balance showed up instantly. No hidden fees, the amount on the receipt matched exactly what I got.",
            "Upgrades feel fair: the chance is shown before you click and the slider is honest. Turned a cheap pistol skin into an M4 at 35%. Love it.",
            "The VIP rakeback actually adds up. I got a few dollars back on my losses this week without asking, it just appeared on my balance.",
            "Clean interface, clear inventory, instant sell-back if I don't like a drop. Everything I need is one tap away. Great work.",
        ),
        "fan": (
            "Really happy with the site overall — fast withdrawals and nice cases. Would love a dark/light toggle and a few more budget cases under a dollar.",
            "Battles are great and the odds feel fair. Only wish: let us filter battles by price, it takes a while to find one in my range.",
        ),
        "idea": (
            "Please add sorting to the inventory by price and rarity. With 200+ skins it's hard to find what I want to upgrade or withdraw.",
            "Idea: a weekly leaderboard for case battles with a small prize pool. It would give everyone a reason to come back on weekends.",
            "Could you add a 'sell all below X' button? Selling cheap drops one by one after a big opening session takes forever.",
        ),
        "glitch": (
            "Small bug: the balance in the header doesn't refresh after selling a skin until I reload the page. The money is there, it just shows the old number.",
            "On mobile the item tooltip in the case preview sometimes covers the 'Open' button. Have to scroll a bit to tap it.",
        ),
        "lag": (
            "Opening a case takes 6–8 seconds to start in the evening. It works, but the waiting kills the vibe when you open several in a row.",
            "Withdrawal queue was slow today — about 40 minutes for a simple rifle skin. It did arrive, but usually it's much faster.",
        ),
        "question": (
            "How do I change my Steam trade link? I moved to a new account and can't find where to update it in the profile settings.",
            "How exactly is the upgrade chance calculated? Is it just the price ratio of the two skins or is there a house edge on top?",
            "What's the minimum deposit with crypto, and do VIP levels count deposits or wagered amount?",
        ),
        "toxic": (
            "The battle chat is getting toxic. A couple of users spam insults at whoever loses and nobody moderates it. Please add a mute or report button.",
        ),
        "crash": (
            "The upgrade page throws an error every time I select a target skin. Tried two browsers, cleared cache, still broken. Can't use upgrades at all.",
            "My case battle froze on round 3 and both my skins disappeared from the inventory view. Balance didn't change either. What happened?",
            "Cases won't open since this morning — the button spins forever and then says 'something went wrong'. My balance is stuck on the site.",
            "After the update the inventory page is blank. I can't sell or withdraw anything, which makes the whole site useless for me right now.",
        ),
        "charge": (
            "Deposited $50 by card two days ago, the money left my bank, but my balance on the site is still zero. Support hasn't replied. Unacceptable.",
            "My withdrawal of a Karambit has been 'pending' for four days. No trade offer came, the skin is gone from my inventory. I want it or my money back.",
        ),
        "ban": (
            "My account was locked right after a big win with no explanation. I never broke any rules. Unlock it and return my skins immediately.",
        ),
    },
    "uk": {
        "praise": (
            "Вивів скін за три хвилини, трейд прийшов майже миттєво. Найшвидший сайт, яким я користувався.",
            "Подобається, що шанси кожного кейсу відкриті, а результат можна перевірити через provably fair. Чесно і прозоро.",
            "Анімація відкриття кейсу дуже плавна навіть на старому телефоні. Момент, коли стрічка сповільнюється на рідкісному скіні, — найкращий.",
            "Підтримка відповіла за пару хвилин і одразу допомогла з трейд-посиланням. Дякую, все чітко!",
            "Сьогодні з третьої спроби вибив ніж із недорогого кейсу і вже вивів його в Steam. Неймовірно!",
            "Щоденний безкоштовний кейс і рейкбек для VIP — дрібниці, заради яких хочеться повертатися щодня.",
            "Вивів ніж за кілька хвилин, трейд надійшов майже одразу. Не очікував такої швидкості — тепер користуюся тільки цим сайтом.",
            "Подобається, що шанси кожного кейсу відкриті, а результат можна перевірити через provably fair. Усе збігається.",
            "Анімація відкриття кейсу чудова, особливо сповільнення перед рідкісним скіном. Навіть на телефоні все плавно.",
            "Підтримка відповіла за кілька хвилин і допомогла з трейд-посиланням. Ввічливо й по суті, дякую!",
            "Щоденний безкоштовний кейс і рейкбек для VIP — приємні бонуси, завдяки яким хочеться повертатися щодня.",
        ),
        "fan": (
            "Загалом дуже задоволений: швидкий вивід і чесні шанси. Хотілося б більше бюджетних кейсів до долара.",
        ),
        "idea": (
            "Додайте, будь ласка, сортування інвентарю за ціною й рідкістю — з сотнею скінів важко знайти потрібний.",
            "Додайте, будь ласка, фільтр батлів за вартістю входу. Зараз доводиться довго шукати відповідний батл.",
            "Було б зручно сортувати інвентар за рідкістю та продавати всі скіни дешевші за вибрану суму однією кнопкою.",
        ),
        "glitch": (
            "Дрібний баг: на телефоні підказка про предмет у кейсі іноді перекриває кнопку «Відкрити».",
            "Невелика помилка: після продажу скіна баланс у верхній панелі оновлюється лише після перезавантаження сторінки.",
        ),
        "lag": (
            "Черга на вивід сьогодні була повільною — близько години на звичайний скін. Прийшов, але зазвичай швидше.",
            "Увечері кейси починають відкриватися із затримкою приблизно десять секунд. Працює, але кілька відкриттів поспіль чекати незручно.",
        ),
        "question": (
            "Яка мінімальна сума поповнення криптовалютою і чи враховуються депозити для рівнів VIP?",
            "Як змінити трейд-посилання Steam? Перейшов на новий акаунт і не можу знайти потрібне налаштування.",
            "Підкажіть, як обчислюється шанс апгрейду: лише за співвідношенням цін скінів чи враховується комісія?",
        ),
        "crash": (
            "Від ранку кейси не відкриваються: кнопка крутиться без кінця, потім пише «щось пішло не так».",
            "Після оновлення сторінка інвентарю порожня — не можу ні продати, ні вивести жодного скіна.",
            "Сторінка апгрейдів показує помилку під час вибору скіна. Спробував різні браузери — апгрейди все одно не працюють.",
            "Батл завис на третьому раунді, а мої скіни зникли з інвентарю. Баланс теж не змінився. Що сталося?",
        ),
        "charge": (
            "Поповнив баланс на 1000 гривень, гроші з картки списали, а на сайті нуль уже дві доби. Підтримка мовчить!",
            "Поповнив баланс на 3000 гривень: гроші з картки списали, а на сайті вже другу добу нуль. Поверніть кошти!",
            "Виведення AK-47 уже три дні має статус «очікується», трейд не надійшов, а скін зник з інвентарю.",
        ),
    },
    "de": {
        "praise": (
            "Auszahlung in unter fünf Minuten, das Tradeangebot kam sofort. So schnell war noch keine Skin-Seite bei mir.",
            "Die Gewinnchancen jeder Kiste sind offen einsehbar und per Provably Fair überprüfbar. Genau so muss das sein.",
            "Case-Battles mit Freunden machen richtig Spaß, und die Animationen laufen auch auf dem Handy flüssig.",
        ),
        "idea": (
            "Bitte fügt einen Filter für Battles nach Einsatz hinzu. Aktuell dauert es ewig, ein passendes Battle zu finden.",
        ),
        "lag": (
            "Abends dauert das Öffnen einer Kiste fast zehn Sekunden. Es funktioniert, aber mehrere hintereinander nerven.",
        ),
        "charge": (
            "Ich habe 40 € per Karte eingezahlt, das Geld ist abgebucht, aber mein Guthaben steht seit zwei Tagen auf null.",
        ),
    },
    "es": {
        "praise": (
            "Retiré mi skin en menos de cinco minutos, la oferta de intercambio llegó al instante. ¡Increíble!",
            "Me encanta que las probabilidades de cada caja sean públicas. Comprobé varias aperturas con provably fair y todo cuadra.",
            "El soporte me respondió en dos minutos y solucionó mi enlace de intercambio enseguida. ¡Muy amables!",
        ),
        "glitch": (
            "Pequeño fallo: el saldo de arriba no se actualiza tras vender una skin hasta que recargo la página.",
        ),
        "crash": (
            "La página de mejoras da error cada vez que elijo una skin objetivo. Probé dos navegadores y nada, no puedo usarla.",
        ),
    },
    "fr": {
        "praise": (
            "Retrait de mon couteau en trois minutes, l'offre d'échange est arrivée tout de suite. Le site le plus rapide que je connaisse.",
            "L'animation d'ouverture des caisses est superbe, même sur mobile. Le ralenti sur l'objet rare, c'est génial.",
            "La caisse gratuite quotidienne et le rakeback VIP me donnent envie de revenir tous les jours.",
            "Les chances d'amélioration sont affichées avant de cliquer, c'est honnête. J'ai transformé un petit skin en M4 !",
        ),
        "idea": (
            "Pourriez-vous ajouter un bouton « tout vendre en dessous de X » ? Vendre les petits drops un par un prend trop de temps.",
        ),
        "lag": (
            "La file d'attente des retraits était lente aujourd'hui, environ quarante minutes. Le skin est arrivé, mais c'est d'habitude plus rapide.",
        ),
        "charge": (
            "Mon retrait est « en attente » depuis quatre jours, aucune offre d'échange reçue et le skin a disparu de mon inventaire.",
        ),
    },
    "it": {
        "praise": (
            "Prelievo della skin in meno di cinque minuti, l'offerta di scambio è arrivata subito. Velocissimi!",
            "Le probabilità di ogni cassa sono pubbliche e verificabili con provably fair. Finalmente un sito trasparente.",
            "Le battaglie di casse con gli amici sono divertentissime e le animazioni sono fluide anche sul telefono.",
        ),
        "glitch": ("Piccolo bug: su mobile il tooltip dell'oggetto copre a volte il pulsante «Apri».",),
        "question": (
            "Come cambio il link di scambio di Steam? Ho un nuovo account e non trovo dove aggiornarlo nel profilo.",
        ),
        "crash": (
            "La mia battaglia si è bloccata al terzo round e le skin sono sparite dall'inventario. Il saldo non è cambiato.",
        ),
    },
    "pl": {
        "praise": (
            "Wypłata skina w niecałe pięć minut, oferta wymiany przyszła od razu. Najszybsza strona, jaką znam.",
            "Szanse każdej skrzynki są jawne i można je sprawdzić przez provably fair. Uczciwie i przejrzyście.",
            "Codzienna darmowa skrzynka i rakeback dla VIP to świetny powód, żeby wracać codziennie.",
        ),
        "idea": (
            "Dodajcie proszę sortowanie ekwipunku według ceny i rzadkości, przy setce skinów ciężko cokolwiek znaleźć.",
        ),
        "lag": (
            "Wieczorem otwieranie skrzynki trwa prawie dziesięć sekund. Działa, ale przy kilku z rzędu to męczące.",
        ),
    },
    "zh": {
        "praise": (
            "提取皮肤不到五分钟，交易报价马上就到了。用过最快的皮肤网站！",
            "每个箱子的概率都是公开的，还能用可验证公平工具核对开箱结果。很透明，很放心。",
        ),
        "fan": ("整体很满意，提取速度快，概率也公平。希望能增加按价格筛选对战的功能。",),
        "glitch": ("小问题：卖掉皮肤后，页面顶部的余额要刷新页面才会更新。",),
        "question": ("请问升级的成功率是怎么计算的？只看两个皮肤的价格比例，还是另外有平台抽成？",),
        "crash": ("从今天早上开始箱子打不开了，按钮一直转圈，最后提示“出错了”。余额被卡在网站上。",),
    },
    "ja": {
        "praise": (
            "スキンの出金が5分もかからず、トレードオファーがすぐに届きました。今まで使った中で一番速いサイトです。",
            "ケースを開けるアニメーションがスマホでもとても滑らかです。レアアイテムの前で減速する瞬間が最高です。",
        ),
        "idea": ("ケースバトルの週間ランキングと小さな賞金を追加してほしいです。週末に戻ってくる理由になります。",),
        "lag": ("夜はケースを開けるのに10秒近くかかります。動作はしますが、続けて開けるとストレスです。",),
        "charge": (
            "カードで5000円入金し、引き落とされたのに、サイトの残高が2日経っても0のままです。至急返金してください！",
        ),
    },
}

#: Draft replies of the demo reviews: one per kind of situation and language.
DEMO_REPLIES: dict[str, dict[str, str]] = {
    "thanks": {
        "en": "Thank you for the kind words! We're glad you enjoy the cases and fast withdrawals — good luck with your next drops!",
        "es": "¡Gracias por tus amables palabras! Nos alegra que disfrutes de las cajas y los retiros rápidos. ¡Suerte con tus próximos drops!",
        "de": "Danke für die netten Worte! Schön, dass dir die Kisten und die schnellen Auszahlungen gefallen — viel Glück bei den nächsten Drops!",
        "fr": "Merci pour ces mots gentils ! Ravis que les caisses et les retraits rapides vous plaisent — bonne chance pour vos prochains drops !",
        "ja": "温かいお言葉をありがとうございます！ケースとスピーディーな出金を楽しんでいただけて嬉しいです。次のドロップも幸運を！",
        "zh": "感谢您的好评！很高兴您喜欢我们的箱子和快速提取。祝您下次开箱好运！",
        "it": "Grazie per le belle parole! Siamo felici che ti piacciano le casse e i prelievi veloci. In bocca al lupo per i prossimi drop!",
        "pl": "Dziękujemy za miłe słowa! Cieszymy się, że podobają Ci się skrzynki i szybkie wypłaty. Powodzenia przy kolejnych dropach!",
        "uk": "Дякуємо за теплі слова! Раді, що вам подобаються кейси та швидкий вивід. Удачі в наступних відкриттях!",
    },
    "sorry": {
        "en": "We're sorry for the trouble! We're checking your deposit, withdrawal or trade offer right now and have escalated it to the payments team. We'll update you shortly.",
        "es": "¡Lamentamos las molestias! Estamos revisando tu depósito, retiro u oferta de intercambio y lo hemos escalado al equipo de pagos. Te escribiremos pronto.",
        "de": "Das tut uns leid! Wir prüfen gerade deine Einzahlung, Auszahlung oder dein Tradeangebot und haben es an das Zahlungsteam weitergeleitet. Wir melden uns bald.",
        "fr": "Nous sommes désolés ! Nous vérifions votre dépôt, retrait ou offre d'échange et l'avons transmis à l'équipe paiements. Nous revenons vers vous rapidement.",
        "ja": "ご迷惑をおかけして申し訳ありません！入金・出金・トレードオファーを確認中で、決済チームに引き継ぎました。まもなくご連絡します。",
        "zh": "给您带来不便，深表歉意！我们正在核查您的充值、提取或交易报价，并已转交支付团队处理，很快会回复您。",
        "it": "Ci scusiamo per il disagio! Stiamo verificando il tuo deposito, prelievo o offerta di scambio e l'abbiamo inoltrato al team pagamenti. Ti aggiorneremo presto.",
        "pl": "Przepraszamy za kłopot! Sprawdzamy Twoją wpłatę, wypłatę lub ofertę wymiany i przekazaliśmy sprawę do działu płatności. Wkrótce się odezwiemy.",
        "uk": "Перепрошуємо за незручності! Ми вже перевіряємо ваше поповнення, вивід або трейд і передали звернення платіжній команді. Незабаром відповімо.",
    },
    "idea": {
        "en": "Thanks for the great idea! We've passed it to the product team — new modes and filters are planned based on player feedback like yours.",
        "es": "¡Gracias por la gran idea! La hemos pasado al equipo de producto: los nuevos modos y filtros se planifican con ideas como la tuya.",
        "de": "Danke für die tolle Idee! Wir haben sie an das Produktteam weitergegeben — neue Modi und Filter planen wir genau nach solchem Feedback.",
        "fr": "Merci pour cette super idée ! Nous l'avons transmise à l'équipe produit : nos nouveaux modes et filtres naissent de retours comme le vôtre.",
        "ja": "素晴らしいアイデアをありがとうございます！プロダクトチームに共有しました。新モードやフィルターはこうした声をもとに計画しています。",
        "zh": "感谢您的好点子！我们已转交产品团队，新玩法和筛选功能正是根据玩家的反馈来规划的。",
        "it": "Grazie per l'ottima idea! L'abbiamo girata al team di prodotto: nuove modalità e filtri nascono proprio da feedback come il tuo.",
        "pl": "Dziękujemy za świetny pomysł! Przekazaliśmy go zespołowi produktu — nowe tryby i filtry planujemy właśnie na podstawie takich opinii.",
        "uk": "Дякуємо за чудову ідею! Передали її команді продукту — нові режими й фільтри ми плануємо саме за такими відгуками.",
    },
    "help": {
        "en": "Thanks for reaching out! You can update your Steam trade link in Profile → Settings, and the FAQ explains upgrade odds, deposits and VIP levels. Write back if anything is unclear.",
        "es": "¡Gracias por escribirnos! Puedes actualizar tu enlace de intercambio en Perfil → Ajustes, y las FAQ explican mejoras, depósitos y niveles VIP.",
        "de": "Danke für deine Nachricht! Deinen Steam-Tradelink änderst du unter Profil → Einstellungen; die FAQ erklären Upgrades, Einzahlungen und VIP-Stufen.",
        "fr": "Merci de nous avoir écrit ! Vous pouvez modifier votre lien d'échange dans Profil → Paramètres ; la FAQ explique améliorations, dépôts et niveaux VIP.",
        "ja": "お問い合わせありがとうございます！トレードURLはプロフィール→設定で変更できます。アップグレード確率、入金、VIPレベルはFAQをご覧ください。",
        "zh": "感谢您的联系！交易链接可在“个人资料 → 设置”中更新，升级概率、充值和VIP等级的说明请见常见问题。",
        "it": "Grazie per averci scritto! Puoi aggiornare il link di scambio in Profilo → Impostazioni; le FAQ spiegano upgrade, depositi e livelli VIP.",
        "pl": "Dziękujemy za wiadomość! Link do wymiany zmienisz w Profil → Ustawienia, a FAQ wyjaśnia szanse ulepszeń, wpłaty i poziomy VIP.",
        "uk": "Дякуємо за звернення! Трейд-посилання можна оновити в Профіль → Налаштування, а в FAQ пояснено шанси апгрейду, поповнення та рівні VIP.",
    },
}

# Seed metadata markers
SEED_PROVIDER = "Automated Test Dataset"
SEED_MODEL = "Simulated Analysis"

#: Arbitrary constant naming the advisory lock that serialises seeding.
SEED_LOCK_KEY = 7_415_302


def generate_email(first_name: str, last_name: str) -> str:
    """Generate a fake email address under a reserved example domain.

    The domains are reserved by RFC 2606, so a demo address shown on a public
    deployment can never belong to a real mailbox.

    Args:
        first_name: The author's first name.
        last_name: The author's last name.

    Returns:
        A synthetic email address.
    """
    domains = ["example.com", "example.org", "example.net"]
    domain = random.choice(domains)
    return f"{first_name.lower()}.{last_name.lower()}@{domain}"


def demo_reviews() -> list[tuple[str, str, DemoProfile]]:
    """List the demo reviews with the analysis that fits each of them.

    Returns:
        One ``(text, language code, profile)`` entry per demo review, in the
        order of :data:`DEMO_TEXTS`.
    """
    return [
        (review_text, language_code, DEMO_PROFILES[kind])
        for language_code, texts_by_kind in DEMO_TEXTS.items()
        for kind, texts in texts_by_kind.items()
        for review_text in texts
    ]


def seed_database(force: bool = False) -> None:
    """Seed the database with 100 skin platform demo reviews.

    The function is **idempotent** by default: if reviews already exist in the
    database the seed is skipped and a message is printed instead.  Pass
    ``force=True`` (or use the ``--force`` CLI flag) to wipe existing reviews
    and insert a fresh dataset.

    Args:
        force: When ``True``, delete all existing reviews before seeding.
    """
    session = SessionLocal()
    try:
        # Two backend replicas starting together must not both see an empty
        # table and seed it twice: the transaction-level advisory lock makes
        # the second one wait and then find the reviews of the first.
        if session.get_bind().dialect.name == "postgresql":
            session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": SEED_LOCK_KEY})

        existing_count: int = session.execute(select(func.count(Review.id))).scalar() or 0

        if existing_count > 0 and not force:
            print(
                f"Database already contains {existing_count} review(s). "
                "Skipping seed to avoid duplicates.\n"
                "  Run with --force to clear existing data and re-seed."
            )
            return

        if force and existing_count > 0:
            print(f"  --force: removing {existing_count} existing review(s)...")
            session.execute(delete(Review))
            session.commit()
            print("  Existing reviews removed.")

        # The shuffle mixes the languages and kinds in the list; every review
        # keeps the analysis that fits its text.
        entries = demo_reviews()
        random.shuffle(entries)

        now = utcnow()
        for review_text, language_code, profile in entries:
            first_name = random.choice(FIRST_NAMES)
            last_name = random.choice(LAST_NAMES)
            email = generate_email(first_name, last_name)

            # Random date within the last 30 days
            days_ago = random.randint(0, 30)
            created_at = now - timedelta(days=days_ago)

            session.add(
                Review(
                    author_name=f"{first_name} {last_name}",
                    email=email,
                    text=review_text,
                    language_code=language_code,
                    created_at_utc=created_at,
                    analysis_status="Pending",
                    rating=profile.rating,
                    priority=profile.priority,
                    category=profile.category,
                    needs_urgent_response=profile.needs_urgent_response,
                    ai_analysis_provider=SEED_PROVIDER,
                    ai_analysis_model=SEED_MODEL,
                    ai_draft_response=DEMO_REPLIES[profile.reply][language_code],
                    ai_draft_response_provider=SEED_PROVIDER,
                    ai_draft_response_model=SEED_MODEL,
                    analyzed_at_utc=created_at + timedelta(minutes=random.randint(1, 10)),
                )
            )

        session.commit()
        print(f"✔ Successfully inserted {len(entries)} reviews into the database")
    finally:
        session.close()


if __name__ == "__main__":
    force_flag: bool = "--force" in sys.argv

    try:
        seed_database(force=force_flag)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        print("Make sure the database is reachable and the schema is migrated.", file=sys.stderr)
        sys.exit(1)
