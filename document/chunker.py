def chunk_document(text, max_chars=6000, overlap_chars=1200):
    paragraphs = [
        paragraph.strip()
        for paragraph in text.split("\n")
        if paragraph.strip()
    ]

    chunks = []
    current_chunk = []
    current_length = 0

    for paragraph in paragraphs:
        paragraph_length = len(paragraph) + 1

        if (
            current_chunk
            and current_length + paragraph_length > max_chars
        ):
            chunks.append("\n".join(current_chunk))

            overlap = []
            overlap_length = 0

            for previous_paragraph in reversed(current_chunk):
                overlap.insert(0, previous_paragraph)
                overlap_length += len(previous_paragraph) + 1

                if overlap_length >= overlap_chars:
                    break

            current_chunk = overlap
            current_length = sum(
                len(item) + 1
                for item in current_chunk
            )

        current_chunk.append(paragraph)
        current_length += paragraph_length

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    return chunks