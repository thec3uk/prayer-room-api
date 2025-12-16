# Spec Requirements: Moderator Prayer Response Page

## Initial Description
Create a Typeform-style interface for moderators to respond to prayer requests one at a time, populating the `response_comment` field which is currently only accessible via Django admin.

## Requirements Discussion

### Core Feature
- **Field to populate**: `response_comment` (currently only via Django admin)
- **Valid requests**: Approved, not flagged, not archived
- **Interface style**: Typeform-style single-request-at-a-time
- **Attribution**: Anonymous - no attribution needed

### Flow Details

**Q: What should happen when the moderator reaches the end of the queue?**
A: Show a fun/comical "no more requests" message with some randomness each time.

**Q: Should moderators be able to skip a prayer request without responding?**
A: Yes, allow skip. No special marking - request just drops out and reappears next session.

**Q: Should there be a progress indicator?**
A: None - pure focus mode.

**Q: Should keyboard shortcuts be supported?**
A: Yes, Cmd/Ctrl+Enter to save and advance.

### Authentication
Use existing staff group (same as existing moderator view).

### Out of Scope
- Notification system (already handled elsewhere)
- Editing previous responses
- Response attribution/tracking which moderator responded
- Progress indicators
- Skip tracking/marking

## Requirements Summary

### Functional Requirements
- Single prayer request displayed at a time (Typeform-style focus mode)
- Text input field for `response_comment`
- Save action that stores response and advances to next request
- Skip action that moves to next request without saving (request reappears next session)
- Keyboard shortcut: Cmd/Ctrl+Enter to save and advance
- Fun/comical randomized message when queue is empty
- Staff authentication required (existing staff group)

### Technical Considerations
- Integration points: Prayer request model, staff authentication system
- Existing system constraints: Must use existing staff group for auth
- Technology preferences: Follow existing moderator view patterns
- Query filter: approved=true, flagged=false, archived=false, response_comment=empty/null

## Visual Assets

Files provided: See `planning/visuals/` folder
