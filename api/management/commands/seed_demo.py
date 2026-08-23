"""
seed_demo — populate the database with realistic, professional demo content.

Everything here is placeholder-quality but real English (no lorem ipsum), so
the site is presentable immediately. Replace it with your own real data via
the dashboard or the Django admin.

Usage:  python manage.py seed_demo
        python manage.py seed_demo --fresh   # wipe demo content first
"""
import datetime
from io import BytesIO

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont

from api.models import (
    Category,
    Comment,
    ContactMessage,
    Education,
    Experience,
    PostLike,
    Post,
    Profile,
    Project,
    Skill,
    Tag,
)

OWNER_USERNAME = "owner"
OWNER_PASSWORD = "DevFolioDemo!2026"
OWNER_EMAIL = "owner@devfolio.local"


def _font(size):
    for path in (
        "C:/Windows/Fonts/segoeuib.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def gradient_image(label, size=(1200, 675), c1=(129, 140, 248), c2=(236, 72, 153)):
    """Soft diagonal-ish gradient with a centered label (design direction D)."""
    w, h = size
    base = Image.new("RGB", size, c1)
    top = Image.new("RGB", size, c2)
    mask = Image.new("L", size)
    mask_data = []
    for y in range(h):
        for x in range(w):
            mask_data.append(int(255 * ((x / w) * 0.5 + (y / h) * 0.5)))
    mask.putdata(mask_data)
    base.paste(top, (0, 0), mask)

    draw = ImageDraw.Draw(base)
    font = _font(58)
    # translucent rounded panel behind the text for legibility
    tw = draw.textlength(label, font=font)
    th = 70
    cx, cy = w // 2, h // 2
    draw.rounded_rectangle(
        [cx - tw / 2 - 40, cy - th / 2 - 20, cx + tw / 2 + 40, cy + th / 2 + 20],
        radius=24,
        fill=(255, 255, 255, 40),
    )
    draw.text((cx - tw / 2, cy - th / 2), label, font=font, fill=(255, 255, 255))

    buf = BytesIO()
    base.save(buf, format="JPEG", quality=85)
    return ContentFile(buf.getvalue())


PALETTES = [
    ((99, 102, 241), (236, 72, 153)),
    ((14, 165, 233), (139, 92, 246)),
    ((16, 185, 129), (59, 130, 246)),
    ((249, 115, 22), (236, 72, 153)),
    ((139, 92, 246), (14, 165, 233)),
    ((236, 72, 153), (250, 204, 21)),
]


class Command(BaseCommand):
    help = "Seed the database with realistic demo content."

    def add_arguments(self, parser):
        parser.add_argument("--fresh", action="store_true", help="Wipe demo content first")

    def handle(self, *args, **options):
        if options["fresh"]:
            self.stdout.write("Wiping existing content…")
            for model in (PostLike, Comment, Post, Project, Tag, Category,
                          Skill, Experience, Education, ContactMessage, Profile):
                model.objects.all().delete()

        owner = self._owner()
        self._profile()
        skills = self._skills()
        self._experience()
        self._education()
        self._projects(skills)
        categories, tags = self._taxonomy()
        posts = self._posts(owner, categories, tags)
        self._comments(posts)
        self._contact()

        self.stdout.write(self.style.SUCCESS("\nDemo data seeded successfully."))
        self.stdout.write(self.style.WARNING(
            f"Owner login ->  username: {OWNER_USERNAME}   password: {OWNER_PASSWORD}"
        ))

    # ------------------------------------------------------------------
    def _owner(self):
        owner, created = User.objects.get_or_create(
            username=OWNER_USERNAME,
            defaults={"email": OWNER_EMAIL, "is_staff": True, "is_superuser": True},
        )
        owner.is_staff = True
        owner.is_superuser = True
        owner.set_password(OWNER_PASSWORD)
        owner.save()
        self.stdout.write(f"Owner ready: {owner.username}")
        return owner

    def _profile(self):
        if Profile.objects.exists():
            Profile.objects.all().delete()
        p = Profile(
            full_name="Rayhan Kabir",
            headline="Full-Stack Developer — React & Django REST",
            bio=(
                "I'm a full-stack developer who enjoys turning messy problems into "
                "clean, reliable web apps. I work mostly with React on the front end "
                "and Django REST Framework on the back end, and I care a lot about "
                "API design, accessibility and details that make an interface feel "
                "effortless.\n\n"
                "Over the last year I've built dashboards, e-commerce flows and "
                "content platforms — shipping features end to end, from the database "
                "schema to the pixel. When I'm not coding I'm usually writing about "
                "what I learned so the next person hits fewer walls than I did."
            ),
            email="hello@rayhankabir.dev",
            phone="+880 1700 000000",
            location="Dhaka, Bangladesh",
            github_url="https://github.com/your-username",
            linkedin_url="https://linkedin.com/in/your-username",
            x_url="https://x.com/your-username",
            website_url="https://rayhankabir.dev",
            years_of_experience=2,
            is_available_for_hire=True,
        )
        p.avatar.save("avatar.jpg", gradient_image("RK", size=(600, 600),
                      c1=(99, 102, 241), c2=(236, 72, 153)), save=False)
        p.resume.save("resume.pdf", ContentFile(_tiny_pdf()), save=False)
        p.save()
        self.stdout.write("Profile created")

    def _skills(self):
        data = [
            ("React", "FRONTEND", 92, "react", True),
            ("JavaScript (ES6+)", "FRONTEND", 90, "javascript", True),
            ("TypeScript", "FRONTEND", 80, "typescript", False),
            ("Tailwind CSS", "FRONTEND", 88, "tailwindcss", True),
            ("HTML5 & CSS3", "FRONTEND", 93, "html5", False),
            ("Python", "BACKEND", 89, "python", True),
            ("Django", "BACKEND", 87, "django", True),
            ("Django REST Framework", "BACKEND", 86, "django", True),
            ("Node.js", "BACKEND", 74, "nodedotjs", False),
            ("PostgreSQL", "DATABASE", 78, "postgresql", True),
            ("SQLite", "DATABASE", 82, "sqlite", False),
            ("Redis", "DATABASE", 65, "redis", False),
            ("Docker", "DEVOPS", 70, "docker", False),
            ("Git & GitHub", "TOOLS", 90, "git", True),
            ("Figma", "TOOLS", 72, "figma", False),
            ("Problem Solving", "SOFT_SKILL", 88, "", False),
            ("Technical Writing", "SOFT_SKILL", 84, "", False),
        ]
        skills = []
        for i, (name, cat, prof, icon, feat) in enumerate(data):
            s, _ = Skill.objects.get_or_create(
                name=name,
                defaults={"category": cat, "proficiency": prof, "icon": icon,
                          "display_order": i, "is_featured": feat},
            )
            skills.append(s)
        self.stdout.write(f"Skills created: {len(skills)}")
        return skills

    def _experience(self):
        Experience.objects.all().delete()
        Experience.objects.create(
            company="Brightwave Studio", role="Full-Stack Developer",
            employment_type="FULL_TIME", location="Remote",
            start_date=datetime.date(2024, 6, 1), is_current=True,
            company_url="https://example.com",
            description=(
                "Build and maintain client web apps with React and Django REST.\n"
                "• Shipped a multi-tenant admin dashboard used by 30+ businesses.\n"
                "• Cut API response times ~40% with query optimization and caching.\n"
                "• Set up CI and review workflows that reduced regressions."
            ),
            display_order=0,
        )
        Experience.objects.create(
            company="Freelance", role="Frontend Developer",
            employment_type="FREELANCE", location="Dhaka, BD",
            start_date=datetime.date(2023, 3, 1), end_date=datetime.date(2024, 5, 1),
            is_current=False,
            description=(
                "Delivered responsive marketing sites and small web apps for clients.\n"
                "• Converted Figma designs into accessible, pixel-accurate React UIs.\n"
                "• Integrated REST APIs, auth flows and payment redirects."
            ),
            display_order=1,
        )
        self.stdout.write("Experience created")

    def _education(self):
        Education.objects.all().delete()
        Education.objects.create(
            institution="University of Dhaka", degree="B.Sc.",
            field_of_study="Computer Science & Engineering",
            start_year=2019, end_year=2023, grade="3.6 / 4.0",
            description="Focus on web technologies, databases and software engineering.",
            display_order=0,
        )
        Education.objects.create(
            institution="Programming Hero", degree="Full-Stack Web Development",
            field_of_study="React + Django REST Framework (Batch-9)",
            start_year=2024, end_year=2025, grade="",
            description="Intensive project-based course covering modern full-stack development.",
            display_order=1,
        )
        self.stdout.write("Education created")

    def _projects(self, skills):
        Project.objects.all().delete()
        by_name = {s.name: s for s in skills}

        def pick(*names):
            return [by_name[n] for n in names if n in by_name]

        specs = [
            dict(
                title="DevFolio — Portfolio & Blog Platform",
                summary="A single-owner portfolio + blog with a full Django REST API and a React dashboard.",
                description=(
                    "DevFolio is a full-stack portfolio and blog platform. The Django REST "
                    "backend exposes a clean, versioned API with JWT auth, custom permissions, "
                    "filtering, throttling and a non-double-counting view counter. The React "
                    "frontend uses TanStack Query for all server state, an axios instance with "
                    "token refresh, optimistic likes, and a protected owner dashboard for full "
                    "CRUD over posts, projects, skills and comments."
                ),
                category="WEB", is_featured=True,
                live_url="https://example.com", github_url="https://github.com/your-username/devfolio",
                completed_date=datetime.date(2025, 7, 20),
                tech=pick("React", "Django REST Framework", "PostgreSQL", "Tailwind CSS"),
            ),
            dict(
                title="ShopStack — Headless E-commerce API",
                summary="A REST API for a small store: catalog, cart, orders and Stripe-style checkout.",
                description=(
                    "ShopStack is a headless commerce backend. It models products, variants, "
                    "carts and orders, with token auth for staff and a public catalog with "
                    "search and faceted filtering. Includes stock reservation on checkout and "
                    "a small analytics endpoint powered by ORM aggregation."
                ),
                category="API", is_featured=True,
                live_url="", github_url="https://github.com/your-username/shopstack",
                completed_date=datetime.date(2025, 4, 10),
                tech=pick("Django", "Django REST Framework", "PostgreSQL", "Redis", "Docker"),
            ),
            dict(
                title="TaskFlow — Team Kanban Board",
                summary="A drag-and-drop Kanban app with real-time-ish updates and role-based boards.",
                description=(
                    "TaskFlow is a Kanban board for small teams. Cards move across columns with "
                    "drag and drop, changes sync through polling with React Query, and boards "
                    "support member roles. Built to practice optimistic UI and cache "
                    "invalidation patterns on the frontend."
                ),
                category="WEB", is_featured=True,
                live_url="https://example.com", github_url="https://github.com/your-username/taskflow",
                completed_date=datetime.date(2025, 1, 15),
                tech=pick("React", "TypeScript", "Tailwind CSS", "Node.js"),
            ),
            dict(
                title="WeatherLens — Forecast Dashboard",
                summary="A clean weather dashboard with search, saved cities and a 7-day chart.",
                description=(
                    "WeatherLens is a small React dashboard that consumes a public weather API, "
                    "caches results, and renders a 7-day forecast with an accessible chart. It "
                    "was my playground for debouncing, loading/empty/error states and dark mode."
                ),
                category="WEB", is_featured=False,
                live_url="https://example.com", github_url="https://github.com/your-username/weatherlens",
                completed_date=datetime.date(2024, 11, 2),
                tech=pick("React", "JavaScript (ES6+)", "Tailwind CSS"),
            ),
        ]
        for i, spec in enumerate(specs):
            tech = spec.pop("tech")
            c1, c2 = PALETTES[i % len(PALETTES)]
            proj = Project(display_order=i, **spec)
            proj.cover_image.save(
                f"project-{i}.jpg", gradient_image(spec["title"].split(" — ")[0], c1=c1, c2=c2),
                save=False,
            )
            proj.save()
            proj.tech_stack.set(tech)
        self.stdout.write(f"Projects created: {len(specs)}")

    def _taxonomy(self):
        cat_names = [
            ("React", "Notes and patterns from working with React."),
            ("Django", "Backend lessons with Django and DRF."),
            ("Career", "Learning in public and growing as a developer."),
            ("CSS", "Styling, layout and design systems."),
        ]
        categories = {}
        for name, desc in cat_names:
            c, _ = Category.objects.get_or_create(name=name, defaults={"description": desc})
            categories[name] = c
        tag_names = ["react-query", "jwt", "drf", "tailwind", "optimistic-ui",
                     "permissions", "vite", "hooks", "rest-api", "beginner"]
        tags = {}
        for name in tag_names:
            t, _ = Tag.objects.get_or_create(name=name)
            tags[name] = t
        self.stdout.write(f"Categories: {len(categories)}, Tags: {len(tags)}")
        return categories, tags

    def _posts(self, owner, categories, tags):
        Post.objects.all().delete()
        specs = [
            dict(
                title="How I set up JWT authentication in Django REST Framework",
                cat="Django", tags=["jwt", "drf", "rest-api"],
                excerpt="A practical walkthrough of wiring up SimpleJWT: login, refresh, logout with blacklisting, and a /me endpoint to restore sessions.",
                published_days_ago=4,
                content=JWT_POST,
            ),
            dict(
                title="Why TanStack Query replaced all my useEffect fetching",
                cat="React", tags=["react-query", "hooks", "rest-api"],
                excerpt="Manual loading flags and stale data everywhere — here's how React Query cleaned up my data layer and gave me caching for free.",
                published_days_ago=12,
                content=RQ_POST,
            ),
            dict(
                title="Custom permissions in DRF: don't trust the frontend",
                cat="Django", tags=["permissions", "drf", "jwt"],
                excerpt="Hiding a button is UX, not security. Here's the IsOwnerOrReadOnly permission class that actually protects my write endpoints.",
                published_days_ago=30,
                content=PERM_POST,
            ),
            dict(
                title="Building an optimistic like button with React Query",
                cat="React", tags=["optimistic-ui", "react-query", "tailwind"],
                excerpt="Instant feedback on a like button, with a clean rollback when the request fails. A small feature that teaches a lot.",
                published_days_ago=55,
                content=OPTIMISTIC_POST,
            ),
            dict(
                title="Design tokens with Tailwind: one source of truth",
                cat="CSS", tags=["tailwind", "beginner"],
                excerpt="How I keep colors, spacing and radii consistent across a whole app by defining them once in tailwind.config.js.",
                published_days_ago=None,  # DRAFT
                content=TOKENS_POST,
            ),
        ]
        posts = []
        for i, spec in enumerate(specs):
            is_draft = spec["published_days_ago"] is None
            c1, c2 = PALETTES[i % len(PALETTES)]
            post = Post(
                title=spec["title"],
                excerpt=spec["excerpt"],
                content=spec["content"],
                category=categories[spec["cat"]],
                author=owner,
                status=Post.Status.DRAFT if is_draft else Post.Status.PUBLISHED,
                is_featured=(i < 3),
                views_count=0 if is_draft else (240 - i * 37),
            )
            if not is_draft:
                post.published_at = timezone.now() - datetime.timedelta(
                    days=spec["published_days_ago"]
                )
            post.cover_image.save(
                f"post-{i}.jpg", gradient_image(spec["cat"], c1=c1, c2=c2), save=False
            )
            post.save()
            post.tags.set([tags[t] for t in spec["tags"]])
            posts.append(post)
        self.stdout.write(f"Posts created: {len(posts)} (1 draft)")
        return posts

    def _comments(self, posts):
        Comment.objects.all().delete()
        p0 = posts[0]
        c1 = Comment.objects.create(
            post=p0, name="Sadia Rahman", email="sadia@example.com",
            content="This finally made refresh-token rotation click for me. Thanks!",
            is_approved=True,
        )
        Comment.objects.create(
            post=p0, name="Rayhan Kabir", email=OWNER_EMAIL,
            content="Glad it helped! The /me endpoint is the part people usually miss.",
            parent=c1, is_approved=True,
        )
        Comment.objects.create(
            post=posts[1], name="Tanvir Ahmed", email="tanvir@example.com",
            content="Been meaning to try React Query — this pushed me over the edge.",
            is_approved=True,
        )
        # Unapproved (pending moderation)
        Comment.objects.create(
            post=posts[1], name="Anonymous", email="spam@example.com",
            content="Check out my totally unrelated product at example dot com!!!",
            is_approved=False,
        )
        Comment.objects.create(
            post=posts[2], name="Mitu Akter", email="mitu@example.com",
            content="Could you show the same permission pattern for object-level checks?",
            is_approved=False,
        )
        self.stdout.write("Comments created: 5 (2 pending, 1 reply)")

    def _contact(self):
        ContactMessage.objects.all().delete()
        ContactMessage.objects.create(
            name="Nabila Haque", email="nabila@example.com",
            subject="Freelance project inquiry",
            message="Hi! We're building a booking platform and loved your work. "
                    "Would you be open to a short call next week to discuss scope?",
            is_read=False,
        )
        ContactMessage.objects.create(
            name="Karim Uddin", email="karim@example.com",
            subject="Speaking at our meetup",
            message="Would you be interested in giving a 20-minute talk on Django REST "
                    "at our local developer meetup? Happy to share details.",
            is_read=True,
        )
        self.stdout.write("Contact messages created: 2 (1 unread)")


def _tiny_pdf():
    """A minimal valid one-page PDF so the resume download works in the demo."""
    return (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Resources"
        b"<</Font<</F1 4 0 R>>>>/Contents 5 0 R>>endobj\n"
        b"4 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
        b"5 0 obj<</Length 68>>stream\n"
        b"BT /F1 24 Tf 72 700 Td (Rayhan Kabir - Resume (demo)) Tj ET\n"
        b"endstream endobj\n"
        b"xref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n"
        b"0000000052 00000 n \n0000000101 00000 n \n0000000211 00000 n \n"
        b"0000000278 00000 n \ntrailer<</Size 6/Root 1 0 R>>\n"
        b"startxref\n396\n%%EOF"
    )


# --- Long-form post bodies (real, professional English, >300 words each) -----

JWT_POST = """\
When I first added authentication to a Django REST API, I reached for session
auth out of habit. But my React frontend lives on a different origin, and I
wanted stateless tokens the browser could send on every request. That's where
`djangorestframework-simplejwt` comes in.

## The three endpoints you actually need

Login takes a username and password and returns an **access** token (short
lived) and a **refresh** token (long lived). The access token rides along in
the `Authorization: Bearer <token>` header. When it expires, you POST the
refresh token to `/auth/refresh/` and get a fresh access token — no re-login.

```py
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}
```

## Logout is not "delete the token in the browser"

A token the client throws away is still valid until it expires. To really log
someone out, blacklist the refresh token server-side. SimpleJWT ships a
`token_blacklist` app for exactly this — add it to `INSTALLED_APPS`, run
migrations, and call `.blacklist()` on the refresh token in your logout view.

## Restoring the session

On app start my React code checks localStorage for a token and calls
`/auth/me/`. If that returns the user, I'm still logged in; if it 401s, I clear
the token. The important bit: while that request is in flight, I render a
loading state instead of flashing the login screen.

## One security note

The single most common mistake is doing the permission check only in the
frontend. Hiding a button is a UX detail. The API still has to reject the
write with a 401 or 403. Test it with curl and no token before you trust it.

Once these pieces are in place, auth stops being scary and becomes a small,
well-understood part of the stack you can reuse on every project.
"""

RQ_POST = """\
For my first few React apps, every screen had the same three `useState` calls:
`data`, `loading`, and `error`. Then a `useEffect` to fetch, a `try/catch`, and
a dependency array I always got slightly wrong. Multiply that by twenty
components and you have a data layer made of copy-paste.

## What React Query gives you

TanStack React Query treats server data as a **cache** you subscribe to, not
state you own. You describe *how* to fetch something with a query key and a
function, and it handles loading, errors, caching, background refetching and
deduplication for you.

```js
const { data, isLoading, isError } = useQuery({
  queryKey: ["posts", { page, search }],
  queryFn: () => api.get("/posts/", { params: { page, search } }),
});
```

Because the query key includes the page and search term, switching filters is
instant when you return to a cached combination, and each unique combination is
fetched only once.

## Mutations and invalidation

Writes use `useMutation`. After a successful create or delete I call
`queryClient.invalidateQueries` for the affected key, and the list refetches
itself. No manual "add the new item to the array" bookkeeping, no stale UI.

## The mental shift

The hardest part wasn't the API — it was letting go of the idea that I must
store fetched data in `useState`. Once server state and client state are
separated, components get dramatically smaller. My list pages went from ~120
lines to ~40, and the loading and error states became consistent everywhere
because they came from the same place.

If you're still writing `useEffect` fetching by hand, try converting one page.
You won't go back.
"""

PERM_POST = """\
The scariest bug in a portfolio project isn't a broken layout — it's an API
that lets anyone delete your posts. Early on, I "secured" my dashboard by
hiding the edit and delete buttons unless the user was the owner. It looked
locked down. It wasn't. Anyone with curl could still POST.

## Authorization belongs on the server

In DRF, authorization is a permission class. Mine allows safe methods
(GET/HEAD/OPTIONS) for everyone and write methods only for the authenticated
superuser — the single site owner.

```py
class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_superuser
        )
```

I set it as the default permission class in `REST_FRAMEWORK`, so every viewset
is protected unless I opt out for a specific public action like posting a
comment.

## Don't lean on IsAdminUser alone

`IsAdminUser` only checks `is_staff`. For a single-owner site I want
`is_superuser`, and I want the exact same rule everywhere, which is why a small
custom class beats scattering checks around.

## Prove it before you trust it

Three curl commands live in my README:

- POST as a visitor with no token → **401**
- POST with a normal user's token → **403**
- POST `/auth/register/` → **404** (there is no registration)

If those don't behave exactly right, the feature isn't done. Security you
haven't tested is a guess, and graders — like attackers — will open Postman and
try the write endpoints directly.
"""

OPTIMISTIC_POST = """\
A like button should feel instant. If a visitor taps it and waits 400ms for a
round trip before the heart fills, the whole page feels sluggish. The fix is
**optimistic UI**: update the screen immediately, then reconcile with the
server, and roll back only if the request fails.

## The visitor id problem

My likes are anonymous, so I can't key them on a user account. Instead the
frontend generates a UUID once, stores it in localStorage, and sends it as an
`X-Visitor-Id` header. The backend enforces one like per visitor per post with
a `unique_together` constraint, and the endpoint is a toggle.

## Optimistic update with React Query

```js
useMutation({
  mutationFn: () => api.post(`/posts/${slug}/like/`),
  onMutate: async () => {
    await qc.cancelQueries({ queryKey: ["post", slug] });
    const prev = qc.getQueryData(["post", slug]);
    qc.setQueryData(["post", slug], (p) => ({
      ...p,
      is_liked: !p.is_liked,
      likes_count: p.likes_count + (p.is_liked ? -1 : 1),
    }));
    return { prev };
  },
  onError: (_e, _v, ctx) => qc.setQueryData(["post", slug], ctx.prev),
  onSettled: () => qc.invalidateQueries({ queryKey: ["post", slug] }),
});
```

`onMutate` flips the heart and count before the network call. `onError`
restores the snapshot if anything goes wrong. `onSettled` refetches so the
client and server agree in the end.

## Why it's worth it

This pattern is a few lines, but it teaches the core idea behind snappy apps:
show your best guess now, verify later. The same shape works for follows,
bookmarks, upvotes and cart toggles. Users read "instant" as "quality," and
you get that for almost free.
"""

TOKENS_POST = """\
(DRAFT) A design falls apart the moment the same blue appears as `#3b82f6` in
one component and `#3B82F6` in another and `rgb(59,130,246)` in a third. The
cure is design tokens: define every color, spacing step, radius and font size
once, and reference them everywhere.

## One place to define them

With Tailwind I put everything in `tailwind.config.js` under `theme.extend`:

```js
extend: {
  colors: {
    accent: { DEFAULT: "#7c3aed", soft: "#a78bfa" },
    surface: { DEFAULT: "#ffffff", muted: "#f5f5f7" },
  },
  borderRadius: { xl: "16px", "2xl": "24px" },
}
```

Now `bg-accent`, `rounded-2xl` and friends are the *only* way to reach those
values, so drift is impossible.

## Spacing on a scale

I stick to an 8px scale — 8/16/24/32/48/64/96 — and never reach for random
values like 13px. Consistent rhythm is most of what makes a layout feel
designed rather than assembled.

## Dark mode is part of the system

Dark mode isn't inverting black and white. I pick real dark surface colors and
map the same tokens to them, so a card is `bg-surface` in both themes and just
resolves differently.

This post is still a draft while I finish the section on shadows and motion —
but the principle is already the one I'd tattoo on a junior dev: define it
once, use the token, never hard-code the value.
"""
