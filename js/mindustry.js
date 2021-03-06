function init() {
  const command_form = document.getElementById('mindustry_form');
  const command_input = document.getElementById('mindustry_command');

  // Connect the command submission
  if(command_input && command_form) {
    command_form.addEventListener('submit', function(){
      let line = document.createElement('p')
      line.innerHTML = '<span class="TERM_FOREGROUND_7_INTENSE">$ </span>' + command_input.value;
      mindustry_output.prepend(line);
      socket.send(command_input.value);
      command_input.value = "";
    });
  }

  // Create WebSocket connection.
  const socket = new WebSocket("ws://127.0.0.1:8080")

  // Connection opened
  socket.addEventListener('open', function (event) {
    socket.send('help');
  });

  // Listen for messages
  socket.addEventListener('message', function (event) {
    const mindustry_output = document.getElementById('mindustry_output');
    let line = document.createElement('p')
    line.innerHTML = convertTerminalCodeToHtml(event.data);
    mindustry_output.prepend(line);
  });
}

function sendHello() {
  socket.send('Hello');
}

// Shell command can have control codes. Some of these mean colours.
function convertTerminalCodeToHtml(line) {
  let htmlline = "";
  let open_spans = 0;
  for(let i = 0; i < line.length; i++) {
    if(line[i] == '\033') {
      let code = line[++i]
      if(code == '[') {
        // This means it's a colour
        while(i < line.length && line[i] != 'm') {
          let colour_code = "";
          for(i++; i < line.length && line[i] != 'm' && line[i] != ';'; i++) {
            colour_code += line[i];
          }
          colour_code = parseInt(colour_code);
          if(colour_code === 0) {
            for(let i = 0; i < open_spans; i++) {
              htmlline += "</span>";
            }
            open_spans = 0;
          }
          if(colour_code === 1) {
            htmlline += '<span class="TERM_FOREGROUND_BOLD">';
            open_spans++;
          }
          else if(colour_code >= 30 && colour_code <= 37) {
            htmlline += '<span class="TERM_FOREGROUND_'+(colour_code-30)+'">';
            open_spans++;
          }
          else if(colour_code >= 90 && colour_code <= 97) {
            htmlline += '<span class="TERM_FOREGROUND_'+(colour_code-90)+'_INTENSE">';
            open_spans++;
          }
        }
      }
    }
    else if(line[i] == '<') {
      htmlline += "&lt;"
    }
    else if(line[i] == '>') {
      htmlline += "&gt;"
    }
    else if(line[i] == '&') {
      htmlline += "&amp;"
    }
    else {
      htmlline += line[i];
    }
  }

  for(let i = 0; i < open_spans; i++) {
    htmlline += "</span>";
  }

  return htmlline
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
