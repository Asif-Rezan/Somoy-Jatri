"""Chronological documentary catalog and deterministic YouTube metadata."""
import math

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


def package(story, topic):
    subject = topic['history_subject']
    sources = '\n'.join(f"{record['title']} — {record['url']}" for record in topic['source_records'])
    story.update(
        title=f'The ENTIRE History of {subject}',
        description=(f"A chronological overview of {subject} ({topic['history_period']}). "
                     f"Illustrations depict historical settings.\n\nSources\n{sources}"),
        tags=[topic['history_label'], topic['category'], 'history documentary', 'Somoy Jatri'],
        search_phrase=subject,
        thumbnail_text=topic['history_label'],
        thumbnail_prompt=(f"{topic['thumbnail_visual_story']}. Ink and color illustrated historical panorama. "
                          'Put the landmark on the left and keep the upper-right sky pale and clear.'),
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
