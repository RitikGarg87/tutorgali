"""
Seed the blog with a small set of evergreen, SEO-focused starter articles.

Idempotent: posts are keyed by slug via get_or_create, so re-running won't
create duplicates (existing posts are left untouched). Author is the first
superuser — create one before running this.

Usage:
    python manage.py seed_blog
"""
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from blog.models import Post


# Each entry maps to Post fields. `body` is admin-authored HTML (rendered with
# |safe in the template, same trust boundary as the admin). related_* hints
# point at real landing pages so the "Find tutors" cross-link CTA resolves
# (see blog/views.py::_related_landing and users/seo_data.py for valid values).
POSTS = [
    {
        'slug': 'how-to-find-a-good-home-tutor-in-india',
        'title': 'How to Find a Good Home Tutor in India (2026 Guide)',
        'category': 'tutor_advice',
        'excerpt': "A step-by-step guide for parents and students on finding a "
                   "verified, affordable home tutor in India — what to check, "
                   "what to ask, and how to avoid common mistakes.",
        'meta_description': "Looking for a home tutor in India? Learn how to find, "
                            "vet, and hire a verified home tutor — qualifications, "
                            "rates, trial classes, and red flags to avoid.",
        'tags': 'home tutor, private tuition, hire tutor, home tuition India',
        'related_city': 'Mumbai',
        'body': """
<p>Finding the right home tutor can make a real difference to a student's
confidence and results — but with so many options, how do you choose well?
This guide walks you through a practical, no-nonsense process for finding a
good home tutor in India.</p>

<h2>1. Be clear about what you need</h2>
<p>Before you start searching, write down the essentials: the student's grade
and board (CBSE, ICSE, State Board, etc.), the subjects they need help with,
whether you prefer classes at home, at the tutor's place, or online, and your
monthly budget. A tutor who is excellent for Class 12 Physics may not be the
right fit for a Class 6 student who needs all-round support.</p>

<h2>2. Prioritise verified tutors</h2>
<p>Anyone can call themselves a tutor. Look for platforms that verify tutor
qualifications and identity before listing them. On TutorGali, every tutor
goes through a manual verification process — including qualification and ID
checks — before their profile is approved.</p>

<h2>3. Check experience and subject fit</h2>
<p>A good profile should tell you the tutor's qualifications, years of
experience, the boards and grades they teach, and their teaching mode. Match
this against your needs rather than picking the first available tutor.</p>

<h2>4. Read reviews from other students</h2>
<p>Genuine reviews from past students are one of the most reliable signals.
Look for comments about punctuality, clarity of explanation, and whether the
student actually improved.</p>

<h2>5. Ask the right questions before you commit</h2>
<ul>
  <li>How do you assess a new student's current level?</li>
  <li>How do you track progress over the term?</li>
  <li>What happens if a class is missed?</li>
  <li>Can we start with a trial class?</li>
</ul>

<h2>6. Start with a trial, then review</h2>
<p>A single trial class tells you a lot: does the tutor explain clearly, is the
student engaged, and is the teaching style a good match? Agree on a short trial
period before committing to a full term.</p>

<h2>Red flags to avoid</h2>
<p>Be cautious of tutors who won't share qualifications, refuse a trial class,
or pressure you into large upfront payments. Transparent rates and a clear
verification process are good signs.</p>

<p>Ready to start? Browse verified tutors near you and compare rates, reviews,
and teaching modes before you connect.</p>
""",
    },
    {
        'slug': 'cbse-vs-icse-vs-state-board-which-is-right',
        'title': 'CBSE vs ICSE vs State Board: Which Is Right for Your Child?',
        'category': 'exam_tips',
        'excerpt': "A clear comparison of CBSE, ICSE, and State Boards in India — "
                   "syllabus depth, exam style, and which suits different students "
                   "and goals.",
        'meta_description': "CBSE vs ICSE vs State Board compared: syllabus, "
                            "difficulty, exam pattern, and how to choose the right "
                            "board for your child in India.",
        'tags': 'CBSE, ICSE, state board, school board comparison',
        'related_board': 'cbse',
        'related_city': 'Mumbai',
        'body': """
<p>Choosing a school board is one of the biggest early decisions parents make.
CBSE, ICSE, and State Boards each have strengths — the "best" one depends on
your child's goals and learning style. Here's an honest comparison.</p>

<h2>CBSE (Central Board of Secondary Education)</h2>
<p>CBSE is the most widely followed board in India. Its syllabus is aligned
with national entrance exams like JEE and NEET, which makes it a popular choice
for students aiming for engineering or medicine. The curriculum is
application-focused and relatively concise.</p>

<h2>ICSE (Indian Certificate of Secondary Education)</h2>
<p>ICSE is known for a broader, more detailed syllabus, with strong emphasis on
English and the humanities. Students often find it more demanding in terms of
depth and volume, which can build strong writing and analytical skills.</p>

<h2>State Boards</h2>
<p>State Boards follow the curriculum set by each state and are usually the most
affordable and locally relevant option. They're a strong choice if your child
plans to appear for state-level entrance exams or scholarships.</p>

<h2>Quick comparison</h2>
<ul>
  <li><strong>Exam style:</strong> CBSE — objective + application; ICSE —
  detailed, essay-heavy; State — varies by state.</li>
  <li><strong>Entrance-exam alignment:</strong> CBSE is closest to JEE/NEET.</li>
  <li><strong>Language &amp; humanities depth:</strong> ICSE leads here.</li>
  <li><strong>Local relevance &amp; cost:</strong> State Boards are strongest.</li>
</ul>

<h2>How to decide</h2>
<p>There's no universally "better" board. Consider your child's strengths,
future goals (national entrance exams vs. state exams), and how they learn.
Whichever board you choose, a tutor experienced in that specific syllabus makes
a big difference — board-specific practice matters more than generic coaching.</p>

<p>Looking for a tutor who knows your board inside out? Find verified tutors
filtered by board near you.</p>
""",
    },
    {
        'slug': 'how-much-does-home-tuition-cost-in-india',
        'title': 'How Much Does Home Tuition Cost in India? (2026 Rates)',
        'category': 'parenting',
        'excerpt': "A realistic breakdown of home tuition costs in India by grade, "
                   "subject, and teaching mode — plus tips to get good value.",
        'meta_description': "How much does home tuition cost in India in 2026? "
                            "Understand tutor rates by grade, subject, and mode "
                            "(online vs at-home) and how to get the best value.",
        'tags': 'tuition cost, tutor fees, home tuition rates, tuition price India',
        'related_city': 'Mumbai',
        'body': """
<p>"How much should I pay for a home tutor?" is one of the most common questions
parents ask. The honest answer: it varies. This guide explains what drives
tuition costs in India and how to judge whether a rate is fair.</p>

<h2>What affects the cost</h2>
<ul>
  <li><strong>Grade level:</strong> Higher grades (11th, 12th) and board-exam
  years usually cost more than primary classes.</li>
  <li><strong>Subject:</strong> Specialised subjects like Physics, Chemistry,
  and Mathematics at senior levels tend to command higher rates.</li>
  <li><strong>Teaching mode:</strong> Online classes are often more affordable
  than at-home tuition, where the tutor factors in travel time.</li>
  <li><strong>Tutor experience:</strong> Highly experienced tutors and those
  with strong track records charge more.</li>
  <li><strong>City:</strong> Rates in metros are generally higher than in
  smaller towns.</li>
</ul>

<h2>How tutors usually price</h2>
<p>On TutorGali, each tutor sets their own monthly rate, shown upfront on their
profile — there are no hidden platform fees. Because rates are transparent, you
can compare several tutors before deciding.</p>

<h2>Getting good value (not just the lowest price)</h2>
<p>The cheapest tutor isn't always the best value. Consider:</p>
<ul>
  <li>Does the tutor have experience with your child's exact board and grade?</li>
  <li>Are reviews positive on clarity and results?</li>
  <li>Is there a trial class so you can judge fit before committing?</li>
</ul>

<h2>Questions to ask about pricing</h2>
<ul>
  <li>Is the rate per month or per session?</li>
  <li>How many classes per week does that include?</li>
  <li>Are study materials or tests included?</li>
</ul>

<p>Compare verified tutors and their transparent monthly rates near you before
you decide.</p>
""",
    },
    {
        'slug': 'how-to-prepare-for-class-10-board-exams',
        'title': 'How to Prepare for Class 10 Board Exams: A Complete Plan',
        'category': 'exam_tips',
        'excerpt': "A practical study plan for Class 10 board exams — timetable, "
                   "subject strategy, revision, and how tuition can help.",
        'meta_description': "A complete Class 10 board exam preparation plan: "
                            "study timetable, subject-wise strategy, revision "
                            "tips, and how a tutor can boost your score.",
        'tags': 'class 10, board exams, study plan, exam preparation',
        'related_subject': 'Mathematics',
        'related_city': 'Mumbai',
        'body': """
<p>Class 10 board exams are the first big public exam most students face. With a
steady plan, they're very manageable. Here's a complete, realistic approach.</p>

<h2>1. Build a weekly timetable</h2>
<p>Don't study everything at once. Split the week so every subject gets regular
attention, with a little more time for the subjects you find hardest. Keep
sessions to 45–60 minutes with short breaks — focused study beats long,
distracted hours.</p>

<h2>2. Understand the exam pattern first</h2>
<p>Before diving into topics, know the marking scheme, chapter weightage, and
question types for your board. This tells you where to invest your time.</p>

<h2>3. Subject strategy</h2>
<ul>
  <li><strong>Mathematics:</strong> Practice daily. Maths rewards consistent
  problem-solving far more than reading.</li>
  <li><strong>Science:</strong> Understand concepts first, then memorise
  definitions, diagrams, and formulae.</li>
  <li><strong>Languages &amp; Social Science:</strong> Focus on structured
  writing, keywords, and previous-year answers.</li>
</ul>

<h2>4. Use previous years' papers</h2>
<p>Solving past papers under timed conditions is one of the highest-impact
things you can do. It builds speed, reveals weak spots, and reduces exam-day
nerves.</p>

<h2>5. Revise smart, not just hard</h2>
<p>Make one-page summaries per chapter, revise them frequently, and re-test
yourself instead of only re-reading. Active recall sticks far better.</p>

<h2>6. When to get a tutor</h2>
<p>If a subject consistently drags your marks down, a focused tutor can fix the
root cause quickly — clearing up misunderstood basics and giving targeted
practice. Even a few sessions before boards can lift a weak subject.</p>

<p>Struggling with a specific subject? Find a verified tutor for it near you and
go into your boards prepared.</p>
""",
    },
    {
        'slug': 'online-vs-offline-tuition-how-to-choose',
        'title': 'Online vs Offline Tuition: Pros, Cons & How to Choose',
        'category': 'subject_guides',
        'excerpt': "Online or in-person tuition? Compare the pros and cons of each "
                   "and decide what works best for your child's learning style.",
        'meta_description': "Online vs offline tuition compared: cost, "
                            "flexibility, focus, and results. Learn which mode "
                            "suits your child and how to choose.",
        'tags': 'online tuition, offline tuition, home tuition, learning mode',
        'related_city': 'Mumbai',
        'body': """
<p>Online tuition has grown enormously, but in-person classes still have real
advantages. Neither is universally better — the right choice depends on the
student. Here's a balanced comparison.</p>

<h2>Online tuition</h2>
<p><strong>Pros:</strong> Access to tutors anywhere (not just your locality),
often more affordable, flexible timing, easy recording and screen-sharing, no
travel time.</p>
<p><strong>Cons:</strong> Needs a reliable internet connection and a quiet
space, can be harder to keep younger children engaged, and some hands-on
subjects are trickier remotely.</p>

<h2>Offline (in-person) tuition</h2>
<p><strong>Pros:</strong> Stronger personal connection, easier to keep young
students focused, immediate hands-on help, fewer tech distractions.</p>
<p><strong>Cons:</strong> Limited to tutors near you, usually higher cost (travel
time), and less scheduling flexibility.</p>

<h2>How to choose</h2>
<ul>
  <li><strong>Age &amp; focus:</strong> Younger children often do better
  in-person; independent older students often thrive online.</li>
  <li><strong>Subject:</strong> Concept-heavy subjects work well online;
  some practical subjects benefit from being in the room.</li>
  <li><strong>Budget &amp; location:</strong> If good local tutors are scarce
  or expensive, online opens up far more choice.</li>
</ul>

<h2>You don't have to pick just one</h2>
<p>Many families mix both — regular online sessions with occasional in-person
classes before exams. On TutorGali, tutors list their teaching mode (online, at
your home, or at the tutor's home), so you can filter for exactly what suits
you.</p>

<p>Compare verified tutors by teaching mode near you and choose what fits your
child best.</p>
""",
    },
]


class Command(BaseCommand):
    help = "Seed the blog with starter SEO articles (idempotent — safe to re-run)."

    def handle(self, *args, **options):
        author = User.objects.filter(is_superuser=True).order_by('id').first()
        if author is None:
            raise CommandError(
                "No superuser found. Create one first:\n"
                "    python manage.py createsuperuser"
            )

        created, skipped = 0, 0
        for data in POSTS:
            _, was_created = Post.objects.get_or_create(
                slug=data['slug'],
                defaults={
                    'title': data['title'],
                    'category': data['category'],
                    'excerpt': data['excerpt'],
                    'meta_description': data.get('meta_description', ''),
                    'tags': data.get('tags', ''),
                    'body': data['body'].strip(),
                    'related_city': data.get('related_city', ''),
                    'related_subject': data.get('related_subject', ''),
                    'related_board': data.get('related_board', ''),
                    'is_published': True,
                    'author': author,
                },
            )
            if was_created:
                created += 1
                self.stdout.write(self.style.SUCCESS(f"  + created: {data['slug']}"))
            else:
                skipped += 1
                self.stdout.write(f"  = exists:  {data['slug']}")

        self.stdout.write(self.style.SUCCESS(
            f"\nDone. {created} created, {skipped} already existed "
            f"(author: {author.username})."
        ))
