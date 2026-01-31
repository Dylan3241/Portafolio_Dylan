import java.util.Scanner;

public class numero_entero {

    public static void main(String[] args) {

        Scanner sc = new Scanner(System.in);
        int numero;

        try {
            System.out.println("Por favor escribe un número entero:");
            numero = sc.nextInt();

            if (numero % 2 == 0) {
                System.out.println("El " + numero + " es par");
            } else {
                System.out.println("El " + numero + " es impar");
            }

        } catch (Exception e) {
            System.out.println("Por favor ingresar un número entero válido");
        } finally {
            sc.close();
        }
    }
}
