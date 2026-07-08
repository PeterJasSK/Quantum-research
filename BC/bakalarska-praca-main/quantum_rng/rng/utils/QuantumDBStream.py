import math
from django.db import transaction
from ..models import QuantumShotResult


def reset_quantum_database():
    with transaction.atomic():
        QuantumShotResult.objects.update(used_bits=0)


class QuantumDBStream:
    def __init__(self):
        # fetch shots ordered by DB id
        self.shots = QuantumShotResult.objects.all().order_by("id")

    def get_random(self, min_val: int, max_val: int):
        """
        Generate a random number in [min_val, max_val],
        consuming bits from DB and updating 'used_bit'.
        """
        n = max_val - min_val + 1
        bits_needed = math.ceil(math.log2(n))

        for shot in self.shots:
            bitstring = shot.bits

            # check if enough bits remain in this shot
            if shot.used_bits + bits_needed <= len(bitstring):
                # slice unused bits
                raw_bits = bitstring[shot.used_bits: shot.used_bits + bits_needed]
                number = int(raw_bits, 2)

                # update pointer and save to DB
                shot.used_bits += bits_needed
                with transaction.atomic():
                    shot.save(update_fields=["used_bits"])

                # rejection sampling
                if number < n:
                    return {
                        "result": min_val + number,
                        "raw_bits": raw_bits,
                        "bits_needed": bits_needed,
                        "used_bit": shot.used_bits,
                        "current_shot": shot.shot_index,
                    }
                else:
                    # if out of range, just try again with updated pointer
                    return self.get_random(min_val, max_val)

        raise ValueError("No more bits available in DB shots!")
