## Setup

This Django project is currently setup using a normal virtualenv running python 3.13. Dependencies are managed via poetry, but I would like to move to uv.

Deployment is handled automatically via Github Actions to a server running dokku

### Development setup

#### Django

I have added a [justfile](https://just.systems/man/en/) to make it easier to get started from a development standpoint.

To get started for the first time (follow the prompts):

```sh
just init
source .venv/bin/activate  # this doesn't work in justfile
just manage createsuperuser
just dev
```

Then coming back again it's just

```sh
source .venv/bin/activate
just dev
```

There is also `just manage` as simple wrapper for running `manage.py` commands

#### Remix

The Remix app is installed as follows:

```sh
npm dev
```

It does require the following `.env` file:

```
AIRTABLE_PAT=<obtained from django>
API_URL=http://localhost:8001/api
```

To get the token visit [here](http://127.0.0.1:8001/admin/authtoken/tokenproxy/) and add a new token, then copy the key into the `.env` file

## Contributions

Please open a PR with your changes to allow a review to happen. Deployments will happen automatically once the PR is merged.

## To do

* migrate to uv tooling
* 404 & 500 handler
* Prayer wall API pagination
- import the historic prayers


## Doing

* location radio buttons are broken

## Done


* custom admin views - neopolitan?
  - actions to mark archived (bulk, indivdual)
- Digest API for all Users
  - email
  - Subject
  - Content
* Drop disallowed host warning to Sentry
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
- Storing the notification toggle for a user.
- User Profile? or Custom Fields in CS?
  2 boolean fields either way
