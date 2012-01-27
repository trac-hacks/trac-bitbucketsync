import json

from trac.core import *
from trac.web import IRequestHandler, IRequestFilter, RequestDone, HTTPNotFound
from trac.versioncontrol import RepositoryManager

from mercurial import ui as mercurial_ui, hg, commands

class BitbucketSync(Component):
    """This component syncs Bitbucket repository with local repository used by Trac."""
    
    implements(IRequestHandler, IRequestFilter)

    # IRequestFilter methods
    def pre_process_request(self, req, handler):
        """Called after initial handler selection, and can be used to change
        the selected handler or redirect request."""

        if self.match_request(req):
            # We disable CSRF protection here and force ourselves as a handler
            req.form_token = None
            return self
        
        return handler

    def post_process_request(req, template, data, content_type):
        """Do any post-processing the request might need; typically adding
        values to the template `data` dictionary, or changing template or
        mime type."""

        return (template, data, content_type)

    # IRequestHandler methods
    def match_request(self, req):
        """Return whether the handler wants to process the given request."""

        return req.method == 'POST' and req.path_info == '/bitbucketsync'

    def process_request(self, req):
        """Process the request."""

        payload = json.loads(req.args.get('payload'))

        repository_name = payload.get('repository', {}).get('name')

        self.env.log.debug("BitbucketSync: Got POST request for repository '%s'", repository_name)

        self._process_repository(repository_name)

        req.send_response(200)
        req.send_header('Content-Type', 'text/plain')
        req.send_header('Content-Length', 0)
        req.end_headers()

        raise RequestDone

    def _process_repository(self, name):
        if not name:
            return

        rm = RepositoryManager(self.env)
        trac_repo = rm.get_repository(name)

        if not trac_repo or not hasattr(trac_repo, 'path'):
            return

        # Global UI instance
        ui = mercurial_ui.ui()

        repo = hg.repository(ui, trac_repo.path)

        # Repo UI instance (with repo configuration)
        ui = repo.ui

        # Pulling from default source (as configured in repo configuration)
        commands.pull(ui, repo)
