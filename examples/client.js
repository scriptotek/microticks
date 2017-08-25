
MicroticksClient = function ( host, consumer_key ) {
	this.service = new MicroticksService( host, consumer_key );

	// Example:

	this.onClick = function( evt ) {
		this.service.trackEvent( 'click', {
			target: $(evt.target).attr('id'),
			clickX: evt.center ? evt.center.x : evt.clientX,
			clickY: evt.center ? evt.center.y : evt.clientY,
		} )
	}.bind( this );

	window.addEventListener( 'click', this.onClick, { passive: true, capture: true } );
}
