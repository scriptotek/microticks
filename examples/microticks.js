
MicroticksService = function ( host, consumer_key ) {

	// We will get a session ID from the server, that we can send with every request.
	this.sessionToken = null;

	// The microticks hostname (e.g. 'http://localhost:5000/')
	this.host = host;

	// Log to console
	this.debug = false;

	// Unique key for this instance
	this.consumerKey = consumer_key;

	// Queue of POST requests
	this.requests = [];

	// Are we currently working on requests from the queue?
	this.busy = false;

	// Is session starting?
	this.sessionStarting = false;
};

MicroticksService.DUMMY_HOST = 'dummy';

// Utility method to join all the arguments using '/' as glue, and avoid double dashes
// if any of the arguments already contains '/'at the beginning or end.
MicroticksService.prototype.urljoin = function () {
	return [].reduce.call(arguments, function( acc, val ) {
		// Convert all arguments to strings by adding  ''
		return (acc + '').replace( /\/+$/, '' ) + '/' + (val + '').replace( /^\/+/, '' );
	});
}

// Run a function during the next tick of the event loop.
MicroticksService.prototype.nextTick = function( f ) {
	setTimeout( f.bind( this ) );
};

// Make a request to the Microticks web API.
// Returns a jquery Promise.
MicroticksService.prototype.post = function ( path, payload ) {
	payload = payload || {};
	payload.ts = (new Date()).toISOString();

	var job = { path: path, payload: payload, deferred: $.Deferred() };

	this.requests.push(job);
	this.sendNextRequest();
	return job.deferred.promise();
}

// Internal method for handling the request queue
MicroticksService.prototype.sendNextRequest = function () {
	if (this.busy || !this.requests.length) {
		return; // we only do one thing at the time
	}

	var job = this.requests.shift();
	job.payload.token = this.sessionToken;
	var url = this.urljoin(this.host, job.path);

	if (this.debug) {
		console.log( '[Microticks] POST ' + url );
		console.log( job.payload );
	}

	if (this.host == MicroticksService.DUMMY_HOST) {
		this.nextTick( this.sendNextRequest );

		return;
	}

	this.busy = true;
	return $.ajax({
		method: "POST",
		url: url,
		dataType: "json",
		data: job.payload,
		cache: false
	})
	.then( function( data, textStatus, jqXHR ) {
		job.deferred.resolve( data, textStatus, jqXHR );
		this.busy = false;
		this.nextTick( this.sendNextRequest );
	}.bind( this ), function( jqXHR, textStatus ){
		job.deferred.reject();
		this.busy = false;
		this.sessionStarting = false;
		console.error("[Microticks] Failed to make request (HTTP status='" + jqXHR.status + " " + jqXHR.statusText + "', message='" + textStatus + "', response='" + jqXHR.responseText + "')");
	}.bind( this ));
}

// Start a new session. Normally this is called when the first event is
// registered, see trackEvent below.
MicroticksService.prototype.startSession = function () {
	if (this.busy || this.sessionStarting) {
		return;
	}
	if (this.host == MicroticksService.DUMMY_HOST) {
		if (this.debug) {
			console.log('[Microticks] Dummy session started');
		}
		this.sessionToken = 'dummy_token';
		return;
	}
	sessionStarting = true;
	this.post('/sessions', {consumer_key: this.consumerKey}).then(function( data, textStatus, jqXHR ) {
		if (this.debug) {
			console.log('[Microticks] Session started');
		}
		this.sessionToken = data.token;
		this.sessionStarting = false;
	}.bind( this ));
}

// Force-stop the current session
MicroticksService.prototype.stopSession = function (reason) {

	if (!this.sessionToken) {
		return;
	}

	this.post('/events', {
		action: 'stopSession',
		data: JSON.stringify( { reason: reason } ),
	});

	return this.post('/sessions/stop').then( function () {
		if (this.debug) {
			console.log('[Microticks] Session stopped');
		}
		this.sessionToken = null;
	}.bind( this ));
}

// Register an event, that will be stored in Microticks.
MicroticksService.prototype.trackEvent = function ( action, data ) {
	if (!this.sessionToken) {
		this.startSession();
	}
	// console.log('[trackEvent]')
	this.post('/events', {
		action: action,
		data: JSON.stringify( data ),
	});
}
