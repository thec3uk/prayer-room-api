## Setup

This Django project is currently setup using a normal virtualenv running python 3.13. Dependencies are managed via poetry, but I would like to move to uv.

Deployment is handled automatically via Github Actions to a server running dokku

## To do

* Drop disallowed host warning to Sentry
* migrate to uv tooling
* 404 & 500 handler
* custom admin views - neopolitan?
  - actions to mark archived (bulk, indivdual)
* Prayer wall pagination
- import the historic prayers

- Digest API for all Users
  - email
  - Subject
  - Content
- Storing the notification toggle for a user.
- User Profile? or Custom Fields in CS?
  2 boolean fields either way

## Doing

* location radio buttons are broken

## Done

* Create Models
* Add Django import export
* Import data - dev
* Create Serializers and Views
  * Actions to increment prayer_count, mark as flagged
* Create Admin views
  - deal with boolean flags <-> datetime for "Flagged" and "Archived"
    - filter boolean on these
* Add some auth for the API
  - can be token auth to begin with?
* Integrate with Remix in a local setup
  * API Pagination for prayers - how does the client work?
* Prayer request
  * Ordering
* Create infra & deploy
* Production role out.
  - setup the new webhooks
    - update zapier hooks
    - test them

* Zapier
  * Webhooks incoming
  * Webhooks outgoing
  * Existing Zaps
    * New submission (OUT)
* sigin with cs
* Sentry
- Github actions
