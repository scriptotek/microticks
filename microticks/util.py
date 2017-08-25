def get_filters(args):
    filters = []
    filterargs = []
    limit = []

    if args.get('ip'):
        filters.append('sessions.ip=?')
        filterargs.append(args.get('ip'))

    if args.get('date'):
        filters.append('sessions.started_at LIKE ?')
        filterargs.append(args.get('date') + '%')

    if args.get('consumer'):
        filters.append('sessions.consumer_id = ?')
        filterargs.append(args.get('consumer'))

    if args.get('sort.desc'):
        limit.append('ORDER BY %s DESC' % args.get('sort.desc'))

    if args.get('sort'):
        limit.append('ORDER BY %s ASC' % args.get('sort'))

    if args.get('limit'):
        limit.append('LIMIT %d' % int(args.get('limit')))

    if args.get('offset'):
        limit.append('OFFSET %d' % int(args.get('offset')))

    if len(filters) == 0:
        return '', (), ' '.join(limit)

    return 'WHERE ' + ' AND '.join(filters), tuple(filterargs), ' '.join(limit)
