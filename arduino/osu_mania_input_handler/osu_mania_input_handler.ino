#include <Arduino.h>

struct Note {
  unsigned long time;
  byte lane;        
};

// Beatmap - exemplo (Hard)
Note beatmap[] = {
  {500, 0}, {750, 1}, {1000, 2}, {1250, 3},
  {1500, 0}, {1750, 2}, {2000, 1}
};
const int totalNotes = sizeof(beatmap) / sizeof(Note);

const int ledPins[] = {2, 3, 4, 5}; 
int currentNote = 0;
unsigned long startTime;

void setup() {
  for (int i = 0; i < 4; i++) {
    pinMode(ledPins[i], OUTPUT);
    digitalWrite(ledPins[i], LOW);
  }

  Serial.begin(115200);
  Serial.println("inicie a musica e pressione reset");
  delay(2000);
  startTime = millis();
}

void loop() {
  unsigned long now = millis() - startTime;

  if (currentNote < totalNotes && now >= beatmap[currentNote].time) {
    int lane = beatmap[currentNote].lane;
    digitalWrite(ledPins[lane], HIGH);
    Serial.print("nota na lane ");
    Serial.print(lane);
    Serial.print(" em ");
    Serial.println(now);

    delay(100); 
    digitalWrite(ledPins[lane], LOW);

    currentNote++;
  }
}
