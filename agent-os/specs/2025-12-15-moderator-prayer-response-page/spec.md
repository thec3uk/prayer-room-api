# Specification: Moderator Prayer Response Page

## Goal
Create a Typeform-style focus interface for moderators to respond to prayer requests one at a time, populating the `response_comment` field that is currently only accessible via Django admin.

## User Stories
- As a moderator, I want to view prayer requests one at a time so that I can focus on crafting thoughtful responses without distraction
- As a moderator, I want to save my response and automatically advance to the next request so that I can efficiently work through the queue
- As a moderator, I want to skip requests I cannot respond to so that I can come back to them later
- As a moderator, I want to use keyboard shortcuts so that I can respond quickly without reaching for the mouse
- As a moderator, I want to see a fun message when the queue is empty so that completing the queue feels rewarding

## Core Requirements
- Display one prayer request at a time in a clean, focused interface
- Provide text input for writing `response_comment`
- Save button stores response and advances to next request
- Skip button advances without saving (request reappears next session)
- Keyboard shortcut: Cmd/Ctrl+Enter to save and advance
- Display randomized fun/comical message when queue is empty
- Require staff authentication (existing staff group)

## Visual Design
No mockups provided. Design should follow Typeform-style principles:
- Clean, minimal interface with ample whitespace
- Single card/container centered on screen
- Large, readable typography for prayer request content
- Prominent text area for response
- Clear action buttons (Save, Skip)
- Smooth transitions between requests
- Full viewport height utilization

### Responsive Breakpoints
- Desktop: Centered card (max-width: 700px)
- Tablet: Centered card with reduced padding
- Mobile: Full-width with minimal margins

## Reusable Components

### Existing Code to Leverage
- `base.html` template with header, nav, and common styles
- `@staff_member_required` decorator from `django.contrib.admin.views.decorators`
- `ListView` pattern from existing `ModerationView` and `FlaggedView`
- HTMX patterns: `hx-post`, `hx-target`, `hx-swap`, `hx-vals`
- Toast notification system via `X-Message` response header
- CSS classes: `.btn`, `.btn-primary`, `.btn-secondary`, `.empty-state`, etc.

### New Components Required
- `prayer_response.html` - Main page template extending `base.html`
- `_prayer_response_content.html` - HTMX-swappable content partial
- `PrayerResponseView` - Django class-based view handling GET/POST

## Technical Approach

### Django View

**URL:** `/prayers/respond/` (name: `prayer-response`)

**View Class:** `PrayerResponseView(View)`
- Protected with `@method_decorator(staff_member_required)`
- Follows patterns from `ModerationView` and `FlaggedView`

**GET Request:**
- Query for next eligible prayer request:
  ```python
  PrayerPraiseRequest.objects.filter(
      approved_at__isnull=False,  # approved
      flagged_at__isnull=True,    # not flagged
      archived_at__isnull=True,   # not archived
  ).filter(
      Q(response_comment__isnull=True) | Q(response_comment='')
  ).order_by('created_at').first()
  ```
- If HTMX request: return `_prayer_response_content.html` partial
- If regular request: return full `prayer_response.html` page

**POST Request:**
- Actions: `respond` (save response) or `skip` (advance without saving)
- For `respond`: Update `response_comment` field on the prayer request
- Return updated content partial with next request (or empty state)
- Set `X-Message` header for toast notification on save

### Templates

**`prayers/prayer_response.html`** (extends `base.html`)
```
- Page title: "Prayer Response"
- Container div with id="prayer-response-content"
- Include _prayer_response_content.html partial
- Extra styles for Typeform-style centered layout
- Extra scripts for Cmd/Ctrl+Enter keyboard shortcut
```

**`prayers/_prayer_response_content.html`** (HTMX partial)
```
If prayer request exists:
  - Centered card with:
    - Prayer request name, type badge, location badge, date
    - Prayer content text (large, readable)
    - Textarea for response_comment
    - Action buttons:
      - "Save & Next" (hx-post with action=respond)
      - "Skip" (hx-post with action=skip)

If no requests:
  - Empty state with randomized fun message
  - "Check back later" subtext
```

### HTMX Interactions

**Save Response:**
```html
<button type="button" class="btn btn-save"
    hx-post="{% url 'prayer-response' %}"
    hx-vals='{"prayer_id": "{{ prayer.id }}", "action": "respond", "response_comment": ""}'
    hx-include="[name=response_comment]"
    hx-target="#prayer-response-content"
    hx-swap="innerHTML swap:0.3s">
    Save & Next
</button>
```

**Skip Request:**
```html
<button type="button" class="btn btn-skip"
    hx-post="{% url 'prayer-response' %}"
    hx-vals='{"prayer_id": "{{ prayer.id }}", "action": "skip"}'
    hx-target="#prayer-response-content"
    hx-swap="innerHTML swap:0.3s">
    Skip
</button>
```

### Keyboard Shortcut (JavaScript)
```javascript
document.addEventListener('keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
        e.preventDefault();
        const saveBtn = document.querySelector('.btn-save');
        if (saveBtn) saveBtn.click();
    }
});
```

### Empty Queue Messages (Randomized)
```python
EMPTY_QUEUE_MESSAGES = [
    "You did it! The prayer inbox is gloriously empty.",
    "No more prayers to respond to... time for a coffee break!",
    "All caught up! You're a prayer response champion.",
    "The queue is empty. Somewhere, angels are high-fiving.",
    "Nothing left! You've responded to everything. Gold star for you!",
    "Empty inbox achieved. Go forth and celebrate!",
    "That's all, folks! The prayer queue has been conquered.",
]
```
Select randomly in view and pass to template context.

## Data Model Details

### Prayer Request Model (existing `PrayerPraiseRequest`)
Key fields relevant to this feature:
- `id`: Primary key
- `name`: Requester's name/identifier
- `content`: The prayer request text
- `response_comment`: Text field to be populated (target field)
- `approved_at`: Timestamp, must not be null (approved)
- `flagged_at`: Timestamp, must be null (not flagged)
- `archived_at`: Timestamp, must be null (not archived)
- `created_at`: Timestamp for ordering
- `type`: Prayer type (prayer/praise)
- `location`: ForeignKey to Location

### Query for Eligible Requests
```python
PrayerPraiseRequest.objects.select_related("location").filter(
    approved_at__isnull=False,
    flagged_at__isnull=True,
    archived_at__isnull=True,
).filter(
    Q(response_comment__isnull=True) | Q(response_comment='')
).order_by('created_at')
```

## Navigation

Add "Respond" link to the nav in `base.html`:
```html
<a href="{% url 'prayer-response' %}" class="nav-link {% if request.resolver_match.url_name == 'prayer-response' %}active{% endif %}">Respond</a>
```

## Out of Scope
- Notification system (already handled elsewhere)
- Editing previous responses after saving
- Response attribution/tracking which moderator responded
- Progress indicators showing queue size
- Skip tracking or marking skipped requests
- Bulk response operations
- Response templates or quick-fill options

## Security Considerations
- All requests require staff authentication via `@staff_member_required` decorator
- Validate that prayer_id belongs to an eligible prayer request before allowing response
- Use Django's CSRF protection (already in base.html via `hx-headers`)
- Response content is stored as-is (no special sanitization needed for admin-only field)

## Success Criteria
- Moderators can respond to prayer requests without accessing Django admin
- Interface shows one request at a time with clean, focused design
- Save advances to next request with smooth HTMX transition
- Skip advances without saving (request remains eligible for next session)
- Keyboard shortcut (Cmd/Ctrl+Enter) works reliably
- Empty queue shows randomized fun message
- Page integrates seamlessly with existing navigation and styling
