"""Chronological documentary catalog and deterministic YouTube metadata."""
import math
import re

from islamic_content import validate_topic


CTA = (' Which topic should Somoy Jatri explore next? '
       'Leave a comment, like this video, and subscribe to Somoy Jatri for more history documentaries.')


def _episode(subject, label, period, category, visual, eras):
    records = []
    claims = []
    for number, (name, url, facts) in enumerate(eras, 1):
        source_id = f'source-{number}'
        records.append({'id': source_id, 'title': name, 'url': url})
        claims.extend({'id': f'era-{number}-{index}', 'source_id': source_id, 'text': fact}
                      for index, fact in enumerate(facts, 1))
    return validate_topic({
        'id': 'timeline-' + subject.lower().replace(' ', '-'), 'kind': 'history',
        'category': category, 'content_pillar': category, 'history_subject': subject,
        'history_label': label, 'history_period': period, 'thumbnail_visual_story': visual,
        'facts': [claim['text'] for claim in claims], 'claims': claims, 'source_records': records,
        'sources': list(dict.fromkeys(record['url'] for record in records)),
    })


def catalog():
    return [
        _episode('Ancient Rome', 'Rome', 'c. 750 BC – AD 476', 'Ancient history',
                 'Colosseum at left, terracotta rooftops and Forum temples across the bottom', [
            ('The Met · Italian Peninsula, 1000–1 BC',
             'https://artistproject.metmuseum.org/toah/ht/04/eust.html', [
                'Rome developed in central Italy in a region shared with other peoples, including the Etruscans.',
                'The traditional foundation date is 753 BC and belongs to Roman tradition.',
                'Roman tradition describes a period of kings before the republic began around 509 BC.',
                'Rome extended its power across the Italian peninsula during the republican period.',
            ]),
            ('The Met · The Roman Republic',
             'https://www.metmuseum.org/en/essays/the-roman-republic', [
                'The republican system included elected magistrates and a senate.',
                'Rome fought Carthage in the Punic Wars and eventually destroyed Carthage in 146 BC.',
                'Roman expansion brought Greek art and cultural influences to Rome.',
                'Julius Caesar was assassinated in 44 BC amid the political crisis of the late Republic.',
            ]),
            ('The Met · The Roman Empire',
             'https://www.metmuseum.org/en/essays/the-roman-empire-27-b-c-393-a-d', [
                'Octavian received the title Augustus in 27 BC and inaugurated the imperial period.',
                'Augustus encouraged an extensive building program in Rome.',
                'Trajan extended Roman rule to its greatest territorial extent.',
                'Hadrian consolidated the frontiers and sponsored major architecture.',
            ]),
            ('The Met · The Roman Empire in late antiquity',
             'https://www.metmuseum.org/en/essays/the-roman-empire-27-b-c-393-a-d', [
                'The third century brought political instability and external pressures.',
                'Diocletian reorganized imperial rule under a system with multiple emperors.',
                'Constantine established a new capital at Constantinople, dedicated in AD 330.',
                'Christianity gained imperial support under Constantine.',
            ]),
            ('The Met · Italian Peninsula, AD 1–500',
             'https://artistproject.metmuseum.org/toah/ht/05/eust.html', [
                'After the death of Theodosius I in 395, separate emperors ruled the east and west.',
                'The Visigoths sacked Rome in 410.',
                'The deposition of Romulus Augustulus in 476 conventionally marks the end of the Western Roman Empire.',
                'The Eastern Roman Empire continued after the end of imperial rule in the West.',
            ]),
        ]),
        _episode('the Ottoman Empire', 'Ottoman Empire', 'c. 1299 – 1922', 'Islamic history',
                 'Istanbul waterfront, a domed Ottoman skyline at left and waterfront buildings below', [
            ('The Met · Anatolia and the Caucasus, 1000–1400',
             'https://www.metmuseum.org/en/toah/ht/07/waa', [
                'The Seljuq sultanate held power in much of Anatolia before the rise of the Ottomans.',
                'Mongol victories weakened the Seljuq state.',
                'Regional principalities arose in Anatolia during the fragmentation of Seljuq power.',
                'The Ottoman principality originated around 1299.',
            ]),
            ('The Met · The Art of the Ottomans before 1600',
             'https://www.metmuseum.org/en/essays/the-art-of-the-ottomans-before-1600', [
                'The early Ottoman state expanded from Anatolia into the Balkans.',
                'The Ottomans made Bursa and then Edirne their capitals before Constantinople.',
                'Mehmed II conquered Constantinople in 1453.',
                'Selim I brought Mamluk Syria and Egypt into the empire.',
            ]),
            ('The Met · The Age of Süleyman',
             'https://www.metmuseum.org/en/essays/the-age-of-suleyman-the-magnificent-r-1520-1566', [
                'Süleyman ruled from 1520 to 1566.',
                'Ottoman armies acquired control over much of Hungary during his reign.',
                'Sinan designed major public buildings across the empire.',
                'Imperial patronage supported architecture and the decorative arts.',
            ]),
            ('The Met · The Art of the Ottomans after 1600',
             'https://www.metmuseum.org/en/essays/the-art-of-the-ottomans-after-1600', [
                'The Mosque of Ahmet I continued traditions associated with the architect Sinan.',
                'The Tulip Period saw distinctive developments in Ottoman court culture.',
                'Ottoman patrons and artists incorporated influences from Europe in the eighteenth century.',
                'Older artistic practices continued alongside newer styles.',
            ]),
            ('Atatürk Research Center · Political Reforms',
             'https://atam.gov.tr/siyasal-devrimler/', [
                'The Grand National Assembly of Turkey opened before the Ottoman sultanate was abolished.',
                'The 1921 constitution established the principle of national sovereignty.',
                'The Ottoman sultanate was abolished on November 1, 1922.',
                'The Republic of Turkey was proclaimed on October 29, 1923.',
            ]),
        ]),
        _episode('Feudal Japan', 'Feudal Japan', '1185 – 1868', 'East Asian history',
                 'Japanese hilltop castle on the left, rooftops and pine trees across the bottom', [
            ('The Met · Kamakura and Nanbokucho Periods',
             'https://www.metmuseum.org/essays/kamakura-and-nanbokucho-periods-1185-1392', [
                'The Kamakura period saw political power shift toward provincial warrior landowners.',
                'A military government ruled from Kamakura while the emperor remained in Kyoto.',
                'The military rulers and their regents patronized religious institutions and the arts.',
                'Supporters of Emperor Go-Daigo overthrew the Kamakura regime in 1333.',
            ]),
            ('The Met · Muromachi Period',
             'https://www.metmuseum.org/essays/muromachi-period-1392-1573', [
                'The Ashikaga shogunate ruled from the Muromachi district of Kyoto.',
                'Ashikaga rulers never extended power as widely as the earlier Kamakura government.',
                'Zen Buddhism influenced education, commerce, and cultural life.',
                'Political upheaval coexisted with innovations in trade and the arts.',
            ]),
            ('The Met · Momoyama Period',
             'https://www.metmuseum.org/essays/momoyama-period-1573-1615', [
                'Oda Nobunaga deposed the last Ashikaga shogun.',
                'Toyotomi Hideyoshi continued the military and political unification of Japan.',
                'The period is associated with imposing castles and lavishly decorated interiors.',
                'Tea culture developed alongside grand displays of wealth and authority.',
            ]),
            ('The Met · Art of the Edo Period',
             'https://www.metmuseum.org/essays/art-of-the-edo-period-1615-1868', [
                'Tokugawa rule was centered on Edo, the city now called Tokyo.',
                'The Edo period was marked by sustained political stability.',
                'Urban merchants supported cultural activity alongside traditional elite patrons.',
                'Woodblock prints became a prominent form of popular art.',
            ]),
            ('National Diet Library · Chronology of Modern Japan',
             'https://www.ndl.go.jp/modern/e/utility/chronology.html', [
                'Commodore Perry reached Japan in 1853.',
                'Japan signed the Treaty of Kanagawa with the United States in 1854.',
                'Tokugawa Yoshinobu returned governing authority to the imperial court in 1867.',
                'The Meiji Restoration replaced shogunal government with a new political order in 1868.',
            ]),
        ]),
    ]


PACKAGING = {
    'Ancient Rome': {
        'hook': 'WHAT SURVIVED?',
        'opening': 'Rome grew from central Italy into an empire. When imperial rule ended in the West, what continued in the East?',
        'tags': ('Roman Republic', 'Roman Empire', 'Punic Wars', 'Augustus', 'Constantinople',
                 'fall of the Western Roman Empire'),
        'chapters': ('Early Rome and the Republic', 'Carthage and the Crisis of the Republic',
                     'Augustus and the Imperial Age', 'Constantine and a New Capital',
                     'The Western Empire Ends'),
    },
    'the Ottoman Empire': {
        'hook': 'WHAT ENDED IT?',
        'opening': 'A frontier principality grew into an empire with its capital at Constantinople. How did Ottoman rule give way to a republic?',
        'tags': ('Ottoman history', 'Constantinople 1453', 'Mehmed II', 'Suleiman the Magnificent',
                 'Ottoman sultanate', 'rise and fall of the Ottoman Empire'),
        'chapters': ('Before the Ottomans', 'Expansion and Constantinople', 'The Age of Suleiman',
                     'Ottoman Culture after 1600', 'The End of the Sultanate'),
    },
    'Feudal Japan': {
        'hook': 'WHO HELD POWER?',
        'opening': 'Japan still had an emperor while shoguns governed from Kamakura, Kyoto and Edo. How did that balance of power end?',
        'tags': ('Japanese history', 'samurai history', 'Kamakura shogunate', 'Tokugawa shogunate',
                 'Edo period', 'Meiji Restoration'),
        'chapters': ('The Rise of Kamakura', 'The Ashikaga Shogunate', 'Unification and Castles',
                     'The Tokugawa Era', 'The Meiji Restoration'),
    },
}


def with_chapters(story, lengths, duration):
    """Use measured chapter audio offsets from the validated render."""
    if not lengths or len(lengths) != len(story['scenes']):
        raise ValueError('Chapter audio timings must match the rendered narration')
    if any(not math.isfinite(value) or value <= 0 for value in lengths):
        raise ValueError('Chapter audio timings must be positive')
    subject = story.get('evidence', {}).get('history_subject')
    info = PACKAGING.get(subject, {})
    if len(lengths) == 20 and info:
        chapters = dict(zip(range(0,20,4),info['chapters']))
    else:
        chapters = {i: ' '.join(scene.get('summary','').split()[:8]).rstrip('.,;:')
                    or f'Chapter {i+1}' for i,scene in enumerate(story['scenes'])}
    lines = []
    elapsed = 0
    for i,length in enumerate(lengths):
        start = int(elapsed)
        if i in chapters and (not lines or start-lines[-1][0] >= 10) and duration-start >= 10:
            lines.append((start,chapters[i]))
        elapsed += length
    if len(lines) < 3:
        raise ValueError('At least three chapter timestamps ten seconds apart are required')
    chapter_text = 'Chapters\n' + '\n'.join(f'{start//60:02}:{start%60:02} {label}' for start,label in lines)
    description = story['description']
    if '\n\nSources\n' in description:
        description = description.replace('\n\nSources\n',f'\n\n{chapter_text}\n\nSources\n',1)
    else:
        description += '\n\n' + chapter_text
    return dict(story,description=description)


def package(story, topic):
    subject = topic['history_subject']
    sources = '\n'.join(f"{record['title']} — {record['url']}" for record in topic['source_records'])
    from history_sequence import artifact_sources
    artifact = artifact_sources(subject)
    if artifact:
        sources += '\n' + artifact
    info = PACKAGING.get(subject, {})
    opening = info.get('opening',f'How did {subject} change over {topic["history_period"]}?')
    hashtag = re.sub(r'[^A-Za-z0-9]','',topic['history_label'])
    tags = list(dict.fromkeys([subject, *info.get('tags',()), topic['category'],
                               f'{topic["history_label"]} documentary','history documentary','Somoy Jatri']))
    story.update(
        title=f'The ENTIRE History of {subject}',
        description=(f"{opening}\n\n"
                     f"Explore {subject} ({topic['history_period']}) through successive eras. "
                     "Maps are schematic and historical scenes are illustrated reconstructions.\n\n"
                     f"Sources\n{sources}\n\n#History #HistoryDocumentary #{hashtag}"),
        tags=tags,
        search_phrase=subject,
        thumbnail_text=info.get('hook','WHAT CHANGED?'),
        thumbnail_prompt=(f"{topic['thumbnail_visual_story']}. Ink and color illustrated historical panorama. "
                          'Put the main landmark large on the left, with a clear silhouette and warm light. '
                          'Leave the upper and middle right pale and clear for lettering. No text.'),
    )


def finalize_title(story, duration_seconds):
    subject = story.get('evidence', {}).get('history_subject')
    if not subject:
        return story
    if not math.isfinite(duration_seconds) or duration_seconds <= 0:
        raise ValueError('History title requires a positive measured video duration')
    minutes = max(1, math.floor(duration_seconds / 60 + 0.5))
    unit = 'Minute' if minutes == 1 else 'Minutes'
    title = f'The ENTIRE History of {subject} in {minutes} {unit}'
    if len(title) > 100:
        raise ValueError('History title exceeds YouTube title limit')
    return dict(story, title=title)
