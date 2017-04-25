def get_filters(args):
    filters = []
    filterargs = []

    if args.get('ip'):
        filters.append('sessions.ip=?')
        filterargs.append(args.get('ip'))

    if args.get('date'):
        filters.append('sessions.started_at LIKE ?')
        filterargs.append(args.get('date') + '%')

    if len(filters) == 0:
        return '', ()

    return 'WHERE ' + ' AND '.join(filters), tuple(filterargs)
