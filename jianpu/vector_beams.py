"""Review beam connections against the native vector input (this score adapter)."""
import xml.etree.ElementTree as E
import pdfplumber


def restore_vector_beams(pdf, root, evidence):
    attached = {}
    with pdfplumber.open(pdf) as document:
        for page_number, page in enumerate(document.pages, 1):
            shapes = [r for r in page.rects if r['fill'] and r['width'] > 2 and .4 < r['height'] < 3]
            shapes += [c for c in page.curves if c['fill'] and c['width'] > 2 and len(c['pts']) == 4
                       and not any(command[0] == 'c' for command in c['path'])]
            heads = [h for row in evidence if row['page'] == page_number for h in row['notes']]
            for head in heads:
                x, y, size = head['x'], head['y'], head['size']
                stems = [line for line in page.lines if line['width'] < .05 and line['height'] > size * .4
                         and x - .5 < line['x0'] < x + size * .35
                         and min(abs(line['top'] - y), abs(line['bottom'] - y)) < 1.6]
                matches = []
                if stems:
                    stem = min(stems, key=lambda line: min(abs(line['top'] - y), abs(line['bottom'] - y)))
                    sx = stem['x0']
                    for index, shape in enumerate(shapes):
                        if not shape['x0'] - .6 <= sx <= shape['x1'] + .6:
                            continue
                        if 'path' in shape:
                            points = shape['pts']; ys = []
                            for a, b in zip(points, points[1:] + points[:1]):
                                if abs(b[0] - a[0]) > .1 and min(a[0], b[0]) - .7 <= sx <= max(a[0], b[0]) + .7:
                                    ys.append(a[1] + (b[1] - a[1]) * (sx - a[0]) / (b[0] - a[0]))
                            if len(ys) < 2 or not .4 < max(ys) - min(ys) < 3:
                                continue
                            beam_y = sum(ys) / len(ys)
                        else:
                            beam_y = (shape['top'] + shape['bottom']) / 2
                        if stem['top'] - 3 <= beam_y <= stem['bottom'] + 3:
                            key = f'{page_number}:{index}'
                            matches.append((abs(beam_y - y), key, shape))
                            attached.setdefault(key, []).append(head)
                head['sourceBeamShapes'] = [key for _, key, _ in sorted(matches, reverse=True)]
                head['sourceBeams'] = []
                for level, (_, key, shape) in enumerate(sorted(matches, reverse=True), 1):
                    head['sourceBeams'].append({'number': level, 'shape': key,
                                               'hook': 'forward hook' if (shape['x0'] + shape['x1']) / 2 > sx else 'backward hook'})
            for head in heads:
                for beam in head['sourceBeams']:
                    members = sorted({round(h['x'], 2) for h in attached[beam['shape']]})
                    index = members.index(round(head['x'], 2))
                    beam['value'] = beam.pop('hook') if len(members) == 1 else 'begin' if index == 0 else 'end' if index == len(members) - 1 else 'continue'
            # A chord's stem can begin at its upper member; all members use its beam.
            for head in heads:
                if not head['sourceBeams']:
                    shared = next((other for other in heads if other['sourceBeams'] and abs(other['x']-head['x']) < .1
                                   and abs(other['y']-head['y']) < 20 and other['small'] == head['small']), None)
                    if shared:
                        head['sourceBeams'] = [dict(beam) for beam in shared['sourceBeams']]
                        head['sourceBeamShapes'] = shared['sourceBeamShapes'][:]
    changes = []
    measures = root.findall('part/measure')
    pitch_order = lambda n: 7 * int(n.findtext('pitch/octave')) + 'CDEFGAB'.index(n.findtext('pitch/step'))
    for row in evidence:
        measure = measures[row['measure'] - 1]
        for small in (False, True):
            heads = [h for h in row['notes'] if h['small'] == small]
            notes = [n for n in measure.findall('note') if n.find('pitch') is not None and (n.find('grace') is not None) == small]
            groups = []
            for n in notes:
                if n.find('chord') is not None: groups[-1].append(n)
                else: groups.append([n])
            notes = [n for group in groups for n in sorted(group, key=pitch_order)]
            assert len(heads) == len(notes), (row['measure'], 'beam review head mismatch')
            for head, note in zip(heads, notes):
                before = [(int(b.get('number', '1')), b.text) for b in note.findall('beam')]
                # Chord members share the first member's rhythmic event.
                after = [(b['number'], b['value']) for b in head['sourceBeams']] if note.find('chord') is None else []
                if small and after:
                    note_type = {1:'eighth', 2:'16th', 3:'32nd', 4:'64th'}[max(level for level, _ in after)]
                    if note.findtext('type') != note_type:
                        changes.append({'kind':'source-grace-type','measure':row['measure'],'before':note.findtext('type'),'after':note_type})
                        note.find('type').text = note_type
                if before != after:
                    changes.append({'kind': 'source-beams', 'measure': row['measure'], 'source': [row['page'], head['x'], head['y']],
                                    'before': before, 'after': after})
                for beam in list(note.findall('beam')): note.remove(beam)
                for level, value in after: E.SubElement(note, 'beam', number=str(level)).text = value
    return changes
