# Task Breakdown: Moderator Prayer Response Page

## Overview
Total Tasks: 21 (across 4 task groups)

This feature creates a Typeform-style focused interface for moderators to respond to prayer requests one at a time, using HTMX for smooth transitions between requests.

## Task List

### Backend Layer

#### Task Group 1: Django View and URL Configuration
**Dependencies:** None

- [x] 1.0 Complete backend view layer
  - [x] 1.1 Write 4-6 focused tests for PrayerResponseView
    - Test GET returns eligible prayer request (approved, not flagged, not archived, no response)
    - Test GET returns empty state when no eligible requests exist
    - Test POST with action=respond saves response_comment and returns next request
    - Test POST with action=skip advances without saving response
    - Test staff authentication is required (redirects unauthenticated users)
    - Test HTMX requests return partial template vs full page
  - [x] 1.2 Create PrayerResponseView class in views.py
    - Import View from django.views
    - Import method_decorator and staff_member_required
    - Implement get() method with eligible prayer query:
      ```python
      PrayerPraiseRequest.objects.select_related("location").filter(
          approved_at__isnull=False,
          flagged_at__isnull=True,
          archived_at__isnull=True,
      ).filter(
          Q(response_comment__isnull=True) | Q(response_comment='')
      ).order_by('created_at').first()
      ```
    - Return full template or HTMX partial based on request headers
  - [x] 1.3 Implement POST handling for respond and skip actions
    - Parse action and prayer_id from POST data
    - For action=respond: validate prayer_id, save response_comment field
    - For action=skip: simply fetch next eligible request without saving
    - Set X-Message header for toast notification on successful save
    - Return next prayer via HTMX partial
  - [x] 1.4 Add EMPTY_QUEUE_MESSAGES constant and random selection
    - Define list of 7 fun/comical messages in view file
    - Select random message when no eligible requests found
    - Pass message to template context
  - [x] 1.5 Add URL route for prayer response page
    - Add path to urls.py: `path('prayers/respond/', PrayerResponseView.as_view(), name='prayer-response')`
  - [x] 1.6 Ensure backend tests pass
    - Run ONLY the 4-6 tests written in 1.1
    - Verify view logic works correctly
    - Do NOT run the entire test suite at this stage

**Acceptance Criteria:**
- The 4-6 tests written in 1.1 pass
- GET request returns eligible prayer or empty state
- POST respond action saves response_comment and advances
- POST skip action advances without saving
- Staff authentication enforced via decorator
- HTMX detection returns appropriate template

---

### Frontend Layer

#### Task Group 2: Templates (Full Page and HTMX Partial)
**Dependencies:** Task Group 1

- [x] 2.0 Complete template layer
  - [x] 2.1 Write 3-5 focused tests for template rendering
    - Test prayer_response.html renders with prayer request data
    - Test _prayer_response_content.html displays prayer details (name, type, location, content)
    - Test empty state partial renders with fun message when no requests
    - Test HTMX attributes are correctly set on buttons
    - Test textarea is present with correct name attribute
  - [x] 2.2 Create prayers/prayer_response.html template
    - Extend base.html
    - Set page title to "Prayer Response"
    - Add container div with id="prayer-response-content"
    - Include _prayer_response_content.html partial
    - Add extra_styles block for Typeform-style layout
    - Add extra_scripts block for keyboard shortcut
  - [x] 2.3 Create prayers/_prayer_response_content.html template
    - If prayer exists: render centered card with:
      - Prayer requester name
      - Type badge (prayer/praise)
      - Location badge
      - Created date
      - Prayer content text (large, readable typography)
      - Textarea for response_comment (name="response_comment")
      - Save & Next button with hx-post, hx-vals, hx-include, hx-target, hx-swap
      - Skip button with hx-post, hx-vals, hx-target, hx-swap
    - If no prayer: render empty state with random fun message and "Check back later" subtext
  - [x] 2.4 Implement HTMX button interactions
    - Save button: `hx-post="{% url 'prayer-response' %}"`, `hx-vals='{"prayer_id": "{{ prayer.id }}", "action": "respond"}'`, `hx-include="[name=response_comment]"`, `hx-target="#prayer-response-content"`, `hx-swap="innerHTML swap:0.3s"`
    - Skip button: `hx-post="{% url 'prayer-response' %}"`, `hx-vals='{"prayer_id": "{{ prayer.id }}", "action": "skip"}'`, `hx-target="#prayer-response-content"`, `hx-swap="innerHTML swap:0.3s"`
  - [x] 2.5 Ensure template tests pass
    - Run ONLY the 3-5 tests written in 2.1
    - Verify templates render correctly
    - Do NOT run the entire test suite at this stage

**Acceptance Criteria:**
- The 3-5 tests written in 2.1 pass
- Full page template extends base.html correctly
- Partial template displays prayer details or empty state
- HTMX attributes configured for smooth transitions
- Textarea captures response_comment input

---

#### Task Group 3: Styling and Interactions
**Dependencies:** Task Group 2

- [x] 3.0 Complete styling and interaction layer
  - [x] 3.1 Write 2-4 focused tests for styling and interactions
    - Test keyboard shortcut (Cmd/Ctrl+Enter) triggers save button click
    - Test page renders correctly at desktop breakpoint (centered card, max-width 700px)
    - Test responsive layout adjusts for mobile (full-width with minimal margins)
    - Test transition animation class is applied on swap
  - [x] 3.2 Add Typeform-style CSS to prayer_response.html extra_styles block
    - Full viewport height utilization (min-height: 100vh)
    - Centered card container with max-width: 700px
    - Ample whitespace and clean minimal design
    - Large, readable typography for prayer content
    - Prominent textarea styling
    - Button styles using existing .btn, .btn-primary, .btn-secondary classes
    - Empty state styling using existing .empty-state class
  - [x] 3.3 Add responsive breakpoint styles
    - Desktop (1024px+): Centered card, max-width 700px, comfortable padding
    - Tablet (768px - 1024px): Centered card with reduced padding
    - Mobile (320px - 768px): Full-width with minimal margins (16px)
  - [x] 3.4 Add smooth transition animations
    - CSS transitions for card appearance (fade-in, slight slide)
    - HTMX swap transition timing (0.3s as specified)
    - Button hover states
  - [x] 3.5 Implement keyboard shortcut in extra_scripts block
    - Listen for keydown event
    - Detect Cmd+Enter (Mac) or Ctrl+Enter (Windows/Linux)
    - Prevent default and trigger click on .btn-save button
    - Handle case where save button doesn't exist (empty state)
  - [x] 3.6 Ensure styling and interaction tests pass
    - Run ONLY the 2-4 tests written in 3.1
    - Verify keyboard shortcut works
    - Verify responsive layout functions correctly
    - Do NOT run the entire test suite at this stage

**Acceptance Criteria:**
- The 2-4 tests written in 3.1 pass
- Typeform-style layout is clean and focused
- Responsive design works across all breakpoints
- Keyboard shortcut (Cmd/Ctrl+Enter) saves and advances
- Smooth transitions between prayer requests

---

### Integration Layer

#### Task Group 4: Navigation Integration and Final Testing
**Dependencies:** Task Groups 1-3

- [x] 4.0 Complete integration and final verification
  - [x] 4.1 Add "Respond" link to navigation in base.html
    - Add nav link: `<a href="{% url 'prayer-response' %}" class="nav-link {% if request.resolver_match.url_name == 'prayer-response' %}active{% endif %}">Respond</a>`
    - Position appropriately among existing nav items
    - Ensure active state styling works
  - [x] 4.2 Review tests from Task Groups 1-3
    - Review the 4-6 tests from Task Group 1 (backend)
    - Review the 3-5 tests from Task Group 2 (templates)
    - Review the 2-4 tests from Task Group 3 (styling/interactions)
    - Total existing tests: approximately 9-15 tests
  - [x] 4.3 Analyze test coverage gaps for critical workflows
    - Identify any untested critical user workflows
    - Focus on end-to-end flow: view request -> type response -> save -> see next
    - Check skip flow: view request -> skip -> see next (same request available later)
    - Verify empty queue state appears correctly
  - [x] 4.4 Write up to 5 additional integration tests if needed
    - Test full respond workflow: load page -> enter response -> save -> verify saved and next loaded
    - Test full skip workflow: load page -> skip -> verify next loaded and original still eligible
    - Test navigation link appears for staff users
    - Test toast notification appears on successful save
    - Test queue completion shows random message
  - [x] 4.5 Run all feature-specific tests
    - Run all tests from Task Groups 1-4
    - Expected total: approximately 14-20 tests
    - Verify all critical workflows pass
    - Do NOT run the entire application test suite
  - [x] 4.6 Manual verification of success criteria
    - Verify moderators can respond without Django admin
    - Verify one request at a time with clean design
    - Verify save advances with smooth HTMX transition
    - Verify skip advances without saving
    - Verify keyboard shortcut works
    - Verify empty queue shows randomized fun message
    - Verify seamless integration with existing nav and styles

**Acceptance Criteria:**
- Navigation link added and active state works
- All feature-specific tests pass (approximately 14-20 tests)
- End-to-end respond workflow functions correctly
- End-to-end skip workflow functions correctly
- All success criteria from spec verified

---

## Execution Order

Recommended implementation sequence:

1. **Task Group 1: Backend View and URL** - Create the Django view with GET/POST handling, authentication, and URL routing. This establishes the API that templates will interact with.

2. **Task Group 2: Templates** - Build the full page template and HTMX partial. This creates the user interface structure that relies on the backend being in place.

3. **Task Group 3: Styling and Interactions** - Add Typeform-style CSS, responsive design, and keyboard shortcuts. This polishes the UI after the core structure is complete.

4. **Task Group 4: Integration and Final Testing** - Add navigation link, review test coverage, fill gaps, and verify all success criteria.

---

## Technical Notes

### Files to Create
- `prayer_room_api/templates/prayers/prayer_response.html`
- `prayer_room_api/templates/prayers/_prayer_response_content.html`

### Files to Modify
- `prayer_room_api/views.py` (add PrayerResponseView)
- `prayer_room_api/urls.py` (add URL route)
- `prayer_room_api/templates/base.html` (add nav link)

### Test File Location
- `prayer_room_api/tests/test_prayer_response.py` (new test file)

### Patterns to Follow
- Use `@method_decorator(staff_member_required)` from existing ModerationView and FlaggedView
- Use `X-Message` header for toast notifications (existing pattern)
- Use HTMX attributes: `hx-post`, `hx-target`, `hx-swap`, `hx-vals`, `hx-include`
- Use existing CSS classes: `.btn`, `.btn-primary`, `.btn-secondary`, `.empty-state`
