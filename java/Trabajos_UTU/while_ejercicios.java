import java.util.Scanner;

public class while_ejercicios {

    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        int opcion;

        System.out.println("Elige el ejercicio a ejecutar:");
        System.out.println("1 - Suma de números (Ejercicio 1)");
        System.out.println("2 - Adivina el número (Ejercicio 2)");
        System.out.println("3 - Promedio de calificaciones (Ejercicio 3)");
        System.out.print("Ingresa tu opción: ");
        opcion = sc.nextInt();

        switch (opcion) {
            case 1:
                sumaNumeros(sc);
                break;
            case 2:
                adivinaNumero(sc);
                break;
            case 3:
                promedioCalificaciones(sc);
                break;
            default:
                System.out.println("Opción inválida.");
        }

        sc.close();
    }

    // Ejercicio 1
    public static void sumaNumeros(Scanner sc) {
        int numero = 0;
        int suma = 0;

        while (true) {
            System.out.print("Ingresa un número entero (negativo para terminar): ");
            numero = sc.nextInt();

            if (numero < 0) {
                break;
            }

            suma += numero;
        }

        System.out.println("La suma de los números ingresados es: " + suma);
    }

    // Ejercicio 2
    public static void adivinaNumero(Scanner sc) {
        int numeroAleatorio = (int) (Math.random() * 10) + 1;
        int intento = 0;

        while (intento != numeroAleatorio) {
            System.out.print("Adivina el número (1-10): ");
            intento = sc.nextInt();

            if (intento < numeroAleatorio) {
                System.out.println("Demasiado bajo.");
            } else if (intento > numeroAleatorio) {
                System.out.println("Demasiado alto.");
            } else {
                System.out.println("¡Felicidades! Adivinaste el número.");
            }
        }
    }

    // Ejercicio 3
    public static void promedioCalificaciones(Scanner sc) {
        int calificacion;
        int suma = 0;
        int contador = 0;

        while (true) {
            System.out.print("Ingresa una calificación (1-10, 0 para terminar): ");
            calificacion = sc.nextInt();

            if (calificacion == 0) {
                break;
            }

            if (calificacion < 1 || calificacion > 10) {
                System.out.println("Calificación inválida. Debe ser entre 1 y 10.");
                continue;
            }

            suma += calificacion;
            contador++;
        }

        if (contador == 0) {
            System.out.println("No se ingresaron calificaciones.");
        } else {
            double promedio = (double) suma / contador;
            System.out.println("El promedio final es: " + promedio);
        }
    }
}
