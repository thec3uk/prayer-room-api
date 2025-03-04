

## To do

* 404 & 500 handler
* migrate to uv tooling
- Github actions
* Sentry

* custom admin views - neopolitan?
  - actions to mark archived (bulk, indivdual)
* Prayer wall pagination
- import the historic prayers

## Doing

* location radio buttons

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
