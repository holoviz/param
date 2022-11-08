import textwrap

def wrap_error_text(text):
    return textwrap.fill(
            text = text,
            width = 80,
            initial_indent='\n',
            expand_tabs = False,
            fix_sentence_endings = True
        )
    
