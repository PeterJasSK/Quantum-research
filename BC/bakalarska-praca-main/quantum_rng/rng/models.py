from django.db import models


class QuantumShotResult(models.Model):
    # Store the full bitstring like "0110101010101010"
    bits = models.CharField(max_length=64)

    # Optionally also store the integer value (derived from bits)
    number = models.BigIntegerField()

    # Track which Braket job this belongs to
    batch_id = models.CharField(max_length=200)

    # Order of the shot (0..999 if you do 1000 shots)
    shot_index = models.IntegerField()

    created_at = models.DateTimeField(auto_now_add=True)

    used_bits = models.IntegerField(max_length=26 , default=0)

    def __str__(self):
        return f"Shot {self.shot_index} | bits={self.bits} | num={self.number}"

