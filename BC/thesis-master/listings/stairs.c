#include <karel.h>

// function definition
void turn_right() {
    set_step_delay(0);
    turn_left();
    turn_left();
    set_step_delay(400);
    turn_left();
}

int main() {
    turn_on("stairs1.kw");

    set_step_delay(400);

    pick_beeper();
    turn_left();
    step();
    // function call
    turn_right();
    step();

    turn_off();
}
