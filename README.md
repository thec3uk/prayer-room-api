

## To do

* Prayer wall pagination
* custom admin views - neopolitan?
  * group for access
  - actions to mark archived (bulk, indivdual)
* Create infra & deploy




## Doing

* sigin with cs
  - allauth

* Zapier
  * Webhooks incoming
  * Webhooks outgoing
  * Existing Zaps
    * Flagged prayer (OUT)
    * New submission (OUT)
    * Discord to AirTable (prayer/praise) (IN)
    * Airtable to Discord (OUT)

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
